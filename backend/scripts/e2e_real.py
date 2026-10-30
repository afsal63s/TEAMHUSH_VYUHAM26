"""Live end-to-end test of OnlyNerd against a running server, with the real LLM (and research, once wired).

Usage:
  uv run python scripts/e2e_real.py --topic "prompt engineering" --level beginner \
      --base-url http://localhost:8000 --max-spend 1.00 [--server-log path/to/server.log]

A Haiku "student" answers the questions. The report results/e2e_<topic>.md is rewritten after every
stage and every notable event (atomically), and results/e2e_<topic>.json holds the raw data.
--max-spend caps this script's own LLM calls (the student). The server's spend happens in the server
process; pass --server-log to copy its latest "LLM usage" line into the report.

Hard errors (HTTP failures, exceptions) stop the run at that stage. Quality checks that fail mark the
stage "fail", are listed under "Problems found", and the run continues so later stages still report.
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)  # config reads .env from the working directory


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--topic", default="prompt engineering")
    p.add_argument("--level", default="beginner", choices=["novice", "beginner", "intermediate", "advanced"])
    p.add_argument("--base-url", default="http://localhost:8000")
    p.add_argument("--max-spend", type=float, default=1.00)
    p.add_argument("--server-log", type=Path, default=None)
    return p.parse_args()


ARGS = parse_args()
os.environ["MAX_SPEND_USD"] = str(ARGS.max_spend)  # caps the student calls in this process

import httpx  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from api.bundles import find_bundle  # noqa: E402
from config import get_settings  # noqa: E402
from generation.llm import _Spend, spend_summary, structured_completion  # noqa: E402

RESULTS = ROOT / "results"
SLOW_SECONDS = 60
GENERATION_TIMEOUT = 8 * 60
RESEARCH_TIMEOUT = 90
POLL_SECONDS = 3  # under uvicorn's 5 s keep-alive timeout
LESSON_WORDS = (120, 200)
LEARNER = "e2e"

STUDENT_SYSTEM = (
    "You are a beginner who has read a few blog posts about this topic. You know some terms but have "
    "real gaps and a few common misconceptions. Answer each multiple-choice question as that person "
    "would: pick exactly one option and a confidence (low, medium or high). Do not try to be perfect."
)

STAGES = [
    (1, "Create course"),
    (2, "Start learner"),
    (3, "Diagnostic"),
    (4, "Research"),
    (5, "Next step"),
    (6, "Time travel and lapse"),
    (7, "Final state"),
]


class StudentPick(BaseModel):
    question_id: str
    chosen_index: int
    confidence: Literal["low", "medium", "high"]


class StudentAnswers(BaseModel):
    answers: list[StudentPick]


class Skip(Exception):
    """The stage cannot run yet; carry on with the next one."""


# --- live report ---

class Report:
    def __init__(self) -> None:
        self.started = datetime.now()
        self.t0 = time.monotonic()
        slug = re.sub(r"[^a-z0-9]+", "_", ARGS.topic.lower()).strip("_")
        self.md_path = RESULTS / f"e2e_{slug}.md"
        self.json_path = RESULTS / f"e2e_{slug}.json"
        self.status = "running"
        self.stages = {n: {"name": name, "status": "pending", "secs": None, "note": "", "lines": []}
                       for n, name in STAGES}
        self.problems: list[str] = []
        self.not_verified: list[str] = []
        self.raw: dict = {"args": {k: str(v) for k, v in vars(ARGS).items()}, "stages": {}}
        self.current = 0
        RESULTS.mkdir(exist_ok=True)

    # terminal transcript + stage details
    def log(self, text: str = "") -> None:
        print(text)
        if self.current:
            self.stages[self.current]["lines"].append(text)

    def problem(self, text: str) -> None:
        where = f"stage {self.current} ({self.stages[self.current]['name']}): " if self.current else ""
        self.problems.append(where + text)
        print(f"  !! PROBLEM: {text}")
        self.save()

    def unverified(self, text: str) -> None:
        if text not in self.not_verified:
            self.not_verified.append(text)

    def server_spend(self) -> str:
        if not ARGS.server_log or not ARGS.server_log.exists():
            return "not available (pass --server-log)"
        lines = [ln for ln in ARGS.server_log.read_text(encoding="utf-8", errors="replace").splitlines()
                 if "LLM usage:" in ln]
        return lines[-1].split("LLM usage:", 1)[1].strip() if lines else "no LLM usage logged yet"

    def server_warnings(self) -> list[str]:
        """WARNING/ERROR lines from --server-log logged since this run started."""
        if not ARGS.server_log or not ARGS.server_log.exists():
            return []
        since = f"{self.started:%Y-%m-%d %H:%M:%S}"
        return [ln.strip() for ln in ARGS.server_log.read_text(encoding="utf-8", errors="replace").splitlines()
                if re.search(r"\b(WARNING|ERROR|CRITICAL)\b", ln) and ln[:19] >= since]

    def render(self) -> str:
        elapsed = time.monotonic() - self.t0
        out = [
            f"# OnlyNerd live E2E: {ARGS.topic}",
            "",
            f"- Started: {self.started:%Y-%m-%d %H:%M:%S}",
            f"- Topic: {ARGS.topic}",
            f"- Level: {ARGS.level}",
            f"- Base URL: {ARGS.base_url}",
            f"- Elapsed: {elapsed:.0f} s",
            f"- LLM spend, this script (student): ${_Spend.cost():.4f} of ${ARGS.max_spend:.2f} ({_Spend.calls} calls)",
            f"- LLM spend, server: {self.server_spend()}",
            f"- Status: **{self.status}**",
            "",
            "| Stage | Status | Seconds | Note |",
            "|---|---|---|---|",
        ]
        for n, s in self.stages.items():
            secs = f"{s['secs']:.1f}" if s["secs"] is not None else ""
            note = s["note"].replace("|", "\\|").replace("\n", " ")
            out.append(f"| {n}. {s['name']} | {s['status']} | {secs} | {note} |")
        for n, s in self.stages.items():
            out += ["", f"## {n}. {s['name']}", ""]
            out += ["```text", *s["lines"], "```"] if s["lines"] else ["_(nothing yet)_"]
        out += ["", "## Problems found", ""]
        out += [f"- {p}" for p in self.problems] or ["_(none so far)_"]
        out += ["", "## Not verified", ""]
        out += [f"- {p}" for p in self.not_verified] or ["_(nothing listed yet)_"]
        return "\n".join(out) + "\n"

    def save(self) -> None:
        for path, text in ((self.md_path, self.render()),
                           (self.json_path, json.dumps(self.raw, indent=2, default=str))):
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, path)


R = Report()


async def run_stage(n: int, fn) -> bool:
    """Run one stage. Returns False if the run must stop."""
    s = R.stages[n]
    R.current, s["status"] = n, "running"
    print(f"\n=== Stage {n}: {s['name']}")
    R.save()
    t = time.monotonic()
    problems_before = len(R.problems)
    try:
        s["note"] = await fn() or ""
        s["status"] = "fail" if len(R.problems) > problems_before and s.get("check_failed") else "pass"
    except Skip as exc:
        s["status"], s["note"] = "skipped", f"skipped: {exc}"
    except Exception as exc:  # noqa: BLE001
        s["status"], s["note"] = "fail", f"{type(exc).__name__}: {exc}"
        R.problems.append(f"stage {n} ({s['name']}) failed: {type(exc).__name__}: {exc}")
        print(f"  !! STAGE {n} ({s['name']}) FAILED: {type(exc).__name__}: {exc}")
    s["secs"] = time.monotonic() - t
    if s["status"] == "fail" and R.status == "running":
        R.status = f"failed at stage {n}"
    R.save()
    return s["status"] != "fail" or s.get("check_failed", False)


def check(cond: bool, what: str) -> None:
    """A quality check: logs ok/FAIL; a failure marks the stage failed but the run continues."""
    R.log(f"  [{'ok' if cond else 'FAIL'}] {what}")
    if not cond:
        R.stages[R.current]["check_failed"] = True
        R.problem(f"check failed: {what}")


# --- HTTP ---

class Api:
    def __init__(self, client: httpx.AsyncClient):
        self.c = client

    async def call(self, method: str, path: str, *, ok404: bool = False, **kw):
        t = time.monotonic()
        try:
            r = await self.c.request(method, path, **kw)
        except (httpx.ReadError, httpx.RemoteProtocolError):
            # uvicorn closes idle keep-alive connections after 5 s; retry once on a fresh one.
            r = await self.c.request(method, path, **kw)
        secs = time.monotonic() - t
        if secs > SLOW_SECONDS:
            R.problem(f"slow request: {method} {path} took {secs:.0f} s")
        if ok404 and r.status_code == 404:
            return None
        if r.status_code >= 400:
            raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:300]}")
        return r.json()


# --- the student ---

def render_questions(questions: list[dict]) -> str:
    lines = []
    for q in questions:
        lines.append(f"[{q['id']}] {q['prompt']}")
        lines += [f"  {i}. {o}" for i, o in enumerate(q["options"])]
    return "\n".join(lines)


async def student(questions: list[dict]) -> list[dict]:
    """One Haiku call answers a round. Missing or invalid picks fall back to option 0, low confidence."""
    user = (f"Topic: {ARGS.topic}\n\nAnswer every question below. Use the exact question ids in brackets "
            f"and the option numbers shown.\n\n{render_questions(questions)}")
    reply = await structured_completion("cheap", STUDENT_SYSTEM, user, StudentAnswers, max_tokens=2000)
    picks = {a.question_id: a for a in reply.answers}
    out = []
    for q in questions:
        a = picks.get(q["id"])
        if a is None or not 0 <= a.chosen_index < len(q["options"]):
            R.problem(f"student gave no valid answer for {q['id']}; using option 0, low confidence")
            out.append({"question_id": q["id"], "chosen_index": 0, "confidence": "low"})
        else:
            out.append({"question_id": q["id"], "chosen_index": a.chosen_index, "confidence": a.confidence})
    R.save()
    return out


# --- content quality heuristics ---

def review_questions(questions: list[dict], correct: dict[str, int] | None = None) -> None:
    for q in questions:
        opts = [o.strip() for o in q["options"]]
        if len(q["prompt"].strip()) < 20:
            R.problem(f"very short question {q['id']}: \"{q['prompt']}\"")
        if len({o.lower() for o in opts}) < len(opts):
            R.problem(f"duplicate options in {q['id']}: {opts}")
        if any(re.search(r"\b(all|none) of the above\b", o, re.I) for o in opts):
            R.problem(f"'all/none of the above' option in {q['id']}: {opts}")
        if correct and q["id"] in correct:
            right = opts[correct[q["id"]]]
            others = [len(o) for i, o in enumerate(opts) if i != correct[q["id"]]]
            if others and len(right) > 1.8 * max(others) and len(right) > 40:
                R.problem(f"correct option is much longer than the distractors (a giveaway) in {q['id']}: "
                          f"\"{q['prompt']}\" correct=\"{right}\"")


def word_count(text: str) -> int:
    return len(text.split())


# --- stages ---

class Ctx:
    cid = ""
    lid = LEARNER
    course: dict = {}
    bundle = None
    key: dict = {}             # question_id -> correct_index (from the server's cached bundle)
    diag: list[dict] = []
    pending: dict | None = None  # the latest StepOut
    placed: list[str] = []
    resources: list[dict] = []

    @property
    def base(self) -> str:
        return f"/courses/{self.cid}/learners/{self.lid}"


C = Ctx()


async def stage1(api: Api) -> str:
    t = time.monotonic()
    course = await api.call("POST", "/courses", json={"prompt": ARGS.topic, "level": ARGS.level})
    C.cid = course["course_id"]
    R.log(f"POST /courses -> {C.cid} status={course['status']}")
    reused = course["status"] == "ready"
    last = None
    while course["status"] == "generating":
        if time.monotonic() - t > GENERATION_TIMEOUT:
            raise TimeoutError(f"course still generating after {GENERATION_TIMEOUT} s")
        await asyncio.sleep(POLL_SECONDS)
        course = await api.call("GET", f"/courses/{C.cid}")
        if course["status"] != last:
            last = course["status"]
        print(f"  ... {course['status']} after {time.monotonic() - t:.0f} s")
    took = time.monotonic() - t
    if course["status"] != "ready":
        raise RuntimeError(f"course status {course['status']} (see server log)")
    C.course = course
    R.raw["course"] = course
    R.log(f"ready after {took:.0f} s{' (reused an existing course, no generation)' if reused else ''}")
    if not reused and took > 180:
        R.problem(f"course generation took {took:.0f} s (expected 1 to 3 minutes)")
    if reused:
        R.unverified("Generation time: the course already existed, so this run did not generate it.")

    C.bundle = find_bundle(ARGS.topic, ARGS.level)
    counts = {}
    if C.bundle:
        C.key = {q.id: q.correct_index for q in C.bundle.questions}
        for q in C.bundle.questions:
            counts[q.concept_id] = counts.get(q.concept_id, 0) + 1
    else:
        R.problem("no cached bundle found in .cache/ or fixtures/; question counts and the answer key are unknown")
    concepts = course["concepts"]
    roots = [c["id"] for c in concepts if not c["prerequisites"]]
    R.log(f"topic: {course['topic']!r}; {len(concepts)} concepts, {len(roots)} roots, "
          f"{sum(counts.values()) if counts else '?'} questions")
    for c in concepts:
        R.log(f"  {c['id']:<36} prereqs={c['prerequisites']} questions={counts.get(c['id'], '?')}")
    check(8 <= len(concepts) <= 12, f"8 to 12 concepts (got {len(concepts)})")
    check(2 <= len(roots) <= 4, f"2 to 4 roots (got {len(roots)}: {roots})")
    if counts:
        thin = {c["id"]: counts.get(c["id"], 0) for c in concepts if counts.get(c["id"], 0) < 5}
        check(not thin, f"every concept has at least 5 questions{f' (thin: {thin})' if thin else ''}")
    R.unverified("Questions per concept come from the server's cached bundle file (.cache/), "
                 "not the API: no route exposes question counts.")
    return f"{len(concepts)} concepts, {len(roots)} roots, ready in {took:.0f} s"


async def stage2(api: Api) -> str:
    try:
        start = await api.call("POST", f"{C.base}/start")
    except RuntimeError as exc:
        if "409" not in str(exc):
            raise
        C.lid = f"{LEARNER}-{datetime.now():%H%M%S}"
        R.problem(f"learner '{LEARNER}' already started this course (earlier run); using '{C.lid}' instead")
        start = await api.call("POST", f"{C.base}/start")
    C.diag = start["questions"]
    R.raw["diagnostic"] = C.diag
    R.log(f"learner {C.lid}: {len(C.diag)} diagnostic questions")
    for q in C.diag:
        R.log(f"\n[{q['id']}] ({q['concept_id']})\n{q['prompt']}")
        for i, o in enumerate(q["options"]):
            R.log(f"   {i}. {o}")
    leaked = [q["id"] for q in C.diag if set(q) != {"id", "concept_id", "prompt", "options"}]
    check(not leaked, f"no correct_index, tags or explanations sent before grading{f' (leaked: {leaked})' if leaked else ''}")
    check({q["concept_id"] for q in C.diag} == {c["id"] for c in C.course["concepts"]},
          "one diagnostic question per concept")
    return f"{len(C.diag)} questions, learner {C.lid}"


def print_graded(res: dict, answers: list[dict], questions: list[dict]) -> None:
    by_id = {q["id"]: q for q in questions}
    conf = {a["question_id"]: a["confidence"] for a in answers}
    chosen = {a["question_id"]: a["chosen_index"] for a in answers}
    for g in res["graded"]:
        q = by_id[g["question_id"]]
        mark = "RIGHT" if g["correct"] else "wrong"
        R.log(f"  {mark:<5} {g['concept_id']:<32} picked {chosen[g['question_id']]} "
              f"(correct {res['correct_indices'][g['question_id']]}), confidence {conf[g['question_id']]}"
              f"{'' if g['correct'] else f', tag {g['chosen_tag']}'}")
        if not g["correct"]:
            R.log(f"        why: {res['explanations'][g['question_id']]}")
        if not res["explanations"].get(g["question_id"], "").strip():
            R.problem(f"empty explanation for {q['id']}")
    R.log(f"new confirmed misconceptions: {res['new_confirmed_misconceptions']}")
    R.log(f"messages: {res['messages']}")
    picked = {g["chosen_tag"] for g in res["graded"] if not g["correct"] and g["chosen_tag"]}
    if picked:
        clash = [m for m in res["messages"] if any(m == f"Misconception {t} resolved." for t in picked)]
        check(not clash, f"no 'resolved' message for a tag picked wrong this round (picked: {sorted(picked)})"
                         f"{f'; got {clash}' if clash else ''}")
    nxt = res["next"]
    R.log(f"next: {nxt['step']['kind']} {nxt['step']['concept_id'] or ''} | reason: {nxt['reason']}")
    if not nxt["reason"].strip():
        R.problem("next step has an empty reason")


async def stage3(api: Api) -> str:
    answers = await student(C.diag)
    res = await api.call("POST", f"{C.base}/attempts", json={"answers": answers})
    R.raw["diagnostic_result"] = res
    print_graded(res, answers, C.diag)
    review_questions(C.diag, res["correct_indices"])
    C.pending = res["next"]
    m = re.match(r"placed as known: ([^;]+);", res["next"]["reason"])
    C.placed = [x.strip() for x in m.group(1).split(",")] if m else []
    state = await api.call("GET", f"{C.base}/state")
    R.log(f"gaps: {state['gaps']}")
    R.log(f"placed as known: {C.placed or 'none'}")
    R.log("mastery: " + ", ".join(f"{k}={v:.2f}" for k, v in res["mastery"].items()))
    right = sum(g["correct"] for g in res["graded"])
    if right == len(res["graded"]):
        R.problem("the beginner student got every diagnostic question right: questions may be too easy")
    if right == 0:
        R.problem("the beginner student got every diagnostic question wrong: questions may be too hard")
    return f"{right}/{len(res['graded'])} right, {len(C.placed)} placed, {len(state['gaps'])} gaps"


def reachable(status: int) -> str:
    if status < 400:
        return "reachable"
    if status in (403, 429):
        return "reachable but blocked"
    return "unreachable"


async def stage4(api: Api) -> str:
    t = time.monotonic()
    resources = None
    while time.monotonic() - t < RESEARCH_TIMEOUT:
        resources = await api.call("GET", f"{C.base}/resources", ok404=True)
        if resources is None:
            R.unverified("Research: GET .../resources is not wired (404), so resources and URL reachability "
                         "were not checked.")
            raise Skip("research route not wired")
        items = resources if isinstance(resources, list) else resources.get("resources", [])
        if items:
            break
        await asyncio.sleep(POLL_SECONDS)
    items = resources if isinstance(resources, list) else (resources or {}).get("resources", [])
    if not items:
        R.problem(f"research returned no resources within {RESEARCH_TIMEOUT} s")
        return "no resources"
    C.resources = items
    R.raw["resources"] = items
    real = 0
    async with httpx.AsyncClient(follow_redirects=True, timeout=10,
                                 headers={"User-Agent": "Mozilla/5.0 OnlyNerd-e2e"}) as web:
        for r in items:
            try:
                status = (await web.get(r["url"])).status_code
                verdict = reachable(status)
            except httpx.HTTPError as exc:
                status, verdict = None, f"unreachable ({type(exc).__name__})"
            real += verdict.startswith("reachable")
            r["reachability"] = verdict
            R.log(f"  {r.get('kind', '?'):<7} {r.get('title', '')[:70]!r}\n          {r['url']} -> {status} {verdict}")
            if not verdict.startswith("reachable"):
                R.problem(f"resource unreachable: {r['url']} ({verdict})")
    state = await api.call("GET", f"{C.base}/state")
    covered = [g for g in state["gaps"]
               if any(r.get("concept_id") == g and r.get("kind") == "article" for r in items)
               and any(r.get("concept_id") == g and r.get("kind") == "video" for r in items)]
    R.log(f"{real}/{len(items)} resources reachable; {len(covered)}/{len(state['gaps'])} gap concepts "
          f"have an article and a video")
    return f"{real}/{len(items)} reachable"


def mastery_changes(before: dict, after: dict) -> None:
    for c, v in after.items():
        if abs(v - before.get(c, v)) > 1e-9:
            R.log(f"  {c}: {before.get(c, 0):.3f} -> {v:.3f}")


async def answer_step(api: Api, step: dict, force_wrong_first: bool = False) -> dict:
    questions = step["questions"]
    answers = await student(questions)
    if force_wrong_first and questions:
        q = questions[0]
        if q["id"] not in C.key:
            raise RuntimeError(f"no answer key for {q['id']}: cannot force a wrong answer")
        answers[0] = {"question_id": q["id"], "chosen_index": (C.key[q["id"]] + 1) % len(q["options"]),
                      "confidence": "medium"}
        R.log(f"  (forced a wrong answer on {q['id']})")
    res = await api.call("POST", f"{C.base}/attempts", json={"answers": answers})
    print_graded(res, answers, questions)
    review_questions(questions, res["correct_indices"])
    return res


async def stage5(api: Api) -> str:
    step = C.pending
    kind = step["step"]["kind"]
    R.log(f"step: {kind} {step['step']['concept_id'] or ''} | reason: {step['reason']}")
    if kind in ("lesson", "fallback"):
        lesson = step["lesson"]
        if not lesson:
            R.problem("lesson step came without a lesson (generation failed? see server log)")
        else:
            words = word_count(lesson["explanation"])
            R.log(f"style: {lesson['style']} | targets: {lesson['targets']} | words: {words}")
            R.log("--- lesson ---")
            R.log(lesson["explanation"])
            R.log("--------------")
            if not LESSON_WORDS[0] <= words <= LESSON_WORDS[1]:
                R.problem(f"lesson length {words} words is outside {LESSON_WORDS}: \"{lesson['explanation'][:160]}...\"")
            if step["step"]["target_misconceptions"] and not lesson["targets"]:
                R.problem("step targets misconceptions but the lesson lists no targets")
            res_urls = {r["url"] for r in lesson["resources"]}
            researched = {r["url"] for r in C.resources}
            if not lesson["resources"]:
                R.problem("lesson has no resources (api/resources.py get_resources is still a stub returning [])")
            R.log(f"lesson resources: {len(res_urls)}; same as researched: "
                  f"{bool(res_urls) and res_urls <= researched}")
            R.raw["lesson"] = lesson
    elif kind in ("done", "session_end"):
        R.log("no material for this step")
        return f"{kind}: nothing to answer"
    if not step["questions"]:
        R.problem(f"{kind} step came with no questions")
        return f"{kind} without questions"
    R.log(f"practice questions: {[q['id'] for q in step['questions']]}")
    for q in step["questions"]:
        R.log(f"\n[{q['id']}] {q['prompt']}")
        for i, o in enumerate(q["options"]):
            R.log(f"   {i}. {o}")
    before = (await api.call("GET", f"{C.base}/state"))
    before_m = {c["concept_id"]: c["p_mastery"] for c in before["concepts"]}
    res = await answer_step(api, step)
    R.raw["practice_result"] = res
    R.log("mastery changes:")
    mastery_changes(before_m, res["mastery"])
    C.pending = res["next"]
    return f"{kind} {step['step']['concept_id']}: {sum(g['correct'] for g in res['graded'])}/{len(res['graded'])} right"


def concept_row(state: dict, cid: str) -> dict:
    return next(c for c in state["concepts"] if c["concept_id"] == cid)


async def stage6(api: Api) -> str:
    if not C.placed:
        R.unverified("Failed-review lapse on a placed concept: the student placed no concepts in the diagnostic.")
    before_state = await api.call("GET", f"{C.base}/state")
    adv = await api.call("POST", f"{C.base}/advance", json={"days": 2})
    R.raw["advance"] = adv
    R.log(f"advanced 2 days: now={adv['now']}")
    R.log(f"due now: {adv['due_now']}")
    state = await api.call("GET", f"{C.base}/state")
    for c in C.placed:
        R.log(f"  placed {c}: retrievability {before_state['retrievability'][c]:.3f} -> "
              f"{state['retrievability'][c]:.3f}, due {state['due'].get(c)}")
    if C.placed:
        # Placement spacing follows confidence: low 1 day, medium 2, high 3.
        stab = {c["concept_id"]: c["stability_days"] for c in state["concepts"]}
        expect = {c for c in C.placed if stab[c] <= 2}
        R.log("  placement spacing: " + ", ".join(f"{c}={stab[c]:g}d" for c in C.placed))
        check(expect == set(C.placed) & set(adv["due_now"]),
              "after 2 days, exactly the placed concepts with 1 or 2 day spacing are due")

    # The API has no "get next step" route: the next step comes back from an attempts call. Finish
    # the pending step's questions (answered normally); the policy then serves due reviews first.
    step = C.pending
    hops = 0
    while step["step"]["kind"] != "review" and step["questions"] and hops < 3:
        R.log(f"finishing pending {step['step']['kind']} {step['step']['concept_id']} to reach the review")
        step = (await answer_step(api, step))["next"]
        hops += 1
    if step["step"]["kind"] != "review":
        R.problem("could not reach a review step through the API (no route returns the next step "
                  f"without submitting answers); last step: {step['step']['kind']}")
        R.unverified("The failed-review (lapse) path through the API.")
        return "no review step reached"

    cid = step["step"]["concept_id"]
    R.log(f"review step: {cid} | reason: {step['reason']} | questions: {[q['id'] for q in step['questions']]}")
    pre = concept_row(await api.call("GET", f"{C.base}/state"), cid)
    res = await answer_step(api, step, force_wrong_first=True)
    post = concept_row(await api.call("GET", f"{C.base}/state"), cid)
    R.raw["lapse"] = {"concept": cid, "before": pre, "after": post, "result": res}
    R.log(f"lapse on {cid}:")
    R.log(f"  {'field':<16}{'before':>22}{'after':>22}")
    for f in ("p_mastery", "stability_days", "lapses", "due_at", "last_reviewed_at"):
        R.log(f"  {f:<16}{str(pre[f])[:21]:>22}{str(post[f])[:21]:>22}")
    R.log(f"next: {res['next']['step']['kind']} {res['next']['step']['concept_id'] or ''} | reason: {res['next']['reason']}")
    nxt = res["next"]["step"]
    check((nxt["kind"], nxt["concept_id"]) == ("lesson", cid),
          f"after the failed review the next step is a lesson on {cid} (got {nxt['kind']} {nxt['concept_id']})")
    check(post["lapses"] == pre["lapses"] + 1, "the failed review counted as a lapse")
    check(post["p_mastery"] <= 0.5, "mastery capped at 0.5 after the lapse")
    check(post["stability_days"] == max(1.0, pre["stability_days"] / 2), "stability halved (min 1 day)")
    C.pending = res["next"]
    return f"lapse on {cid}: mastery {pre['p_mastery']:.2f} -> {post['p_mastery']:.2f}"


async def stage7(api: Api) -> str:
    state = await api.call("GET", f"{C.base}/state")
    R.raw["final_state"] = state
    R.log(f"{'concept':<34}{'mastery':>8}{'recall':>8}{'stab.':>7}{'tries':>6}{'lapses':>7}")
    for c in state["concepts"]:
        R.log(f"{c['concept_id']:<34}{c['p_mastery']:>8.2f}{state['retrievability'][c['concept_id']]:>8.2f}"
              f"{c['stability_days']:>7.1f}{c['attempts']:>6}{c['lapses']:>7}")
    R.log(f"pace: {state['pace']} | days_left: {state['days_left']} | needs_help: {state['needs_help']}")
    R.log(f"gaps: {state['gaps']}")
    for field in ("history", "learning_rate"):
        if field in state:
            v = state[field]
            R.log(f"{field}: {len(v) if field == 'history' else v}")
        else:
            R.log(f"{field}: not in the state response yet (skipped)")
            R.unverified(f"'{field}' in GET .../state: the field does not exist yet.")
    return f"{state['pace'].get('mastered')}/{state['pace'].get('total')} mastered"


async def main() -> int:
    password = get_settings().MASTER_PASSWORD.get_secret_value()
    headers = {"X-Master-Password": password} if password else {}
    if not password:
        R.unverified("Master password: MASTER_PASSWORD is empty in this process, so no header was sent.")
    R.save()
    print(f"report: {R.md_path}")
    stages = {1: stage1, 2: stage2, 3: stage3, 4: stage4, 5: stage5, 6: stage6, 7: stage7}
    async with httpx.AsyncClient(base_url=ARGS.base_url, headers=headers, timeout=300) as client:
        api = Api(client)
        try:
            health = (await client.get("/health")).json()
            print(f"health: {health}")
        except httpx.HTTPError as exc:
            R.status = "failed at stage 0 (server unreachable)"
            R.problems.append(f"server unreachable at {ARGS.base_url}: {exc}")
            R.save()
            print(f"server unreachable: {exc}")
            return 1
        for n, fn in stages.items():
            keep_going = await run_stage(n, lambda fn=fn: fn(api))
            if not keep_going:
                for later in range(n + 1, len(STAGES) + 1):
                    R.stages[later]["status"], R.stages[later]["note"] = "skipped", f"stage {n} failed"
                break

    if R.status == "running":
        R.status = "passed"
    over = _Spend.cost() > ARGS.max_spend
    if over:
        R.problem(f"student spend ${_Spend.cost():.4f} passed --max-spend ${ARGS.max_spend:.2f}")
    for line in R.server_warnings():
        R.problem(f"server log: {line[:400]}")
    if not ARGS.server_log:
        R.unverified("Server-side warnings (e.g. generation validation retries): no --server-log given.")
    R.unverified("Lesson and question quality beyond the automatic heuristics (length, duplicates, "
                 "giveaway options): read the quoted text above.")
    R.current = 0
    R.save()

    print("\n=== Summary")
    print(f"{'stage':<28}{'status':<10}{'secs':>7}  note")
    for n, s in R.stages.items():
        secs = f"{s['secs']:.1f}" if s["secs"] is not None else ""
        print(f"{f'{n}. ' + s['name']:<28}{s['status']:<10}{secs:>7}  {s['note']}")
    print(f"\nstatus: {R.status}")
    print(spend_summary(), f"(limit ${ARGS.max_spend:.2f})")
    print(f"server LLM usage: {R.server_spend()}")
    print(f"problems: {len(R.problems)}")
    print(f"report: {R.md_path}\nraw:    {R.json_path}")
    return 0 if R.status == "passed" and not over else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
