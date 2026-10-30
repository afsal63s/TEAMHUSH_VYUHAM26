"""Step-by-step documented trace of OnlyNerd against a server this script launches itself.

Usage: uv run python scripts/trace_real.py

Writes docs/TRACE_prompt_engineering.md (rewritten atomically after every step) and
docs/TRACE_prompt_engineering.json (raw data). Every step is one HTTP request; for each one the
document shows the request, the response, the server log lines in that window (LLM tokens, research
calls, warnings), the learner state read straight from Mongo, what changed, an independent
recomputation of the numbers (no core/ import), and the brain's decision.

Never writes the master password or any API key: headers are redacted and every written text is
scrubbed of secret values.
"""

import importlib.metadata as md
import json
import math
import os
import platform
import re
import secrets
import subprocess
import sys
import threading
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import httpx  # noqa: E402
from pymongo import MongoClient  # noqa: E402

from api.bundles import find_bundle  # noqa: E402
from config import get_settings  # noqa: E402
from generation import prompt_hash  # noqa: E402
from generation.llm import INPUT_USD_PER_M, OUTPUT_USD_PER_M  # noqa: E402

TOPIC, LEVEL, LEARNER = "prompt engineering", "beginner", "trace"
BASE = "http://127.0.0.1:8000"
DOCS = ROOT / "docs"
MD_PATH = DOCS / "TRACE_prompt_engineering.md"
JSON_PATH = DOCS / "TRACE_prompt_engineering.json"
SERVER_CMD = ("import logging; logging.basicConfig(level=logging.INFO); import uvicorn; "
              "uvicorn.run('main:app', port=8000)")
TRUNCATE = 6000
SLOW_SECONDS = 5
GEN_TIMEOUT = 8 * 60

# Independent model (same numbers as the spec, not imported from core/)
SLIP, GUESS, GUESS_LOW, LEARN, THR = 0.1, 0.25, 0.5, 0.15, 0.85
PLACE_DAYS = {"low": 1.0, "medium": 2.0, "high": 3.0}
SESSION_CAP, ROUND_CAP = 15, 3
TOL_P, TOL_R = 1e-9, 1e-3

SETTINGS = get_settings()
PASSWORD = SETTINGS.MASTER_PASSWORD.get_secret_value() or secrets.token_urlsafe(16)
SECRETS = [s for s in (PASSWORD, SETTINGS.ANTHROPIC_API_KEY.get_secret_value(),
                       SETTINGS.TAVILY_API_KEY.get_secret_value(),
                       SETTINGS.YOUTUBE_API_KEY.get_secret_value()) if s]
ROLE_MODEL = {"strong": SETTINGS.MODEL_STRONG, "cheap": SETTINGS.MODEL_CHEAP, "local": SETTINGS.MODEL_LOCAL}


def scrub(text: str) -> str:
    for s in SECRETS:
        text = text.replace(s, "***")
    return text


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:.6g}"
    if isinstance(v, datetime):
        return v.isoformat(timespec="seconds")
    return str(v)


# --- server with captured log ---

class Server:
    def __init__(self) -> None:
        self.lines: list[tuple[float, str]] = []
        self.proc: subprocess.Popen | None = None

    def start(self) -> None:
        try:
            httpx.get(f"{BASE}/health", timeout=1)
            raise RuntimeError("port 8000 is already serving; stop that server first")
        except httpx.HTTPError:
            pass
        env = {**os.environ, "MASTER_PASSWORD": PASSWORD, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
        self.proc = subprocess.Popen([sys.executable, "-c", SERVER_CMD], cwd=ROOT, env=env, text=True,
                                     encoding="utf-8", errors="replace",
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1)
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        for line in self.proc.stdout:
            self.lines.append((time.monotonic(), scrub(line.rstrip())))

    def window(self, t0: float, t1: float) -> list[str]:
        return [ln for t, ln in self.lines if t0 <= t <= t1 + 0.3]

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def external_calls(lines: list[str]) -> dict:
    llm = []
    for ln in lines:
        m = re.search(r"(\w+) call: (\d+) in / (\d+) out tokens", ln)
        if m:
            role, tin, tout = m.group(1), int(m.group(2)), int(m.group(3))
            llm.append({"role": role, "model": ROLE_MODEL.get(role, "?"), "in": tin, "out": tout,
                        "usd": (tin * INPUT_USD_PER_M + tout * OUTPUT_USD_PER_M) / 1e6})
    return {
        "llm": llm,
        "anthropic_http": sum("api.anthropic.com" in ln for ln in lines),
        "tavily": [ln for ln in lines if "tavily" in ln.lower()],
        "youtube": [ln for ln in lines if "youtube" in ln.lower()],
        "retries": [ln for ln in lines if re.search(r"retry|retrying|transient", ln, re.I)],
        "warnings": [ln for ln in lines if re.match(r"(WARNING|ERROR|CRITICAL)", ln) or "Traceback" in ln],
    }


# --- independent model ---

def bkt(p: float, correct: bool, confidence: str | None) -> float:
    guess = GUESS_LOW if correct and confidence == "low" else GUESS
    if correct:
        post = p * (1 - SLIP) / (p * (1 - SLIP) + (1 - p) * guess)
    else:
        post = p * SLIP / (p * SLIP + (1 - p) * (1 - guess))
    return post + (1 - post) * LEARN


def retrievability(c: dict, now: datetime) -> float:
    if c.get("last_reviewed_at") is None or c.get("stability_days", 0) <= 0:
        return 1.0
    t = (now - c["last_reviewed_at"]).total_seconds() / 86400
    return 0.9 ** (t / c["stability_days"])


def expected_round(prev: dict, graded: list[dict], confidence: dict[str, str | None], now: datetime) -> dict:
    """Expected concept fields after one attempts round, from the state before it."""
    concepts = deepcopy(prev["concepts"])
    diagnostic = all(c["attempts"] == 0 for c in concepts.values())
    by: dict[str, list[dict]] = {}
    for g in graded:
        by.setdefault(g["concept_id"], []).append(g)
    events = {}
    for cid, answers in by.items():
        c = concepts.setdefault(cid, {"p_mastery": 0.2, "attempts": 0, "stability_days": 0.0, "lapses": 0,
                                      "last_reviewed_at": None, "due_at": None, "failed_rounds": 0})
        was_m = c["p_mastery"] >= THR
        was_due = c.get("due_at") is not None and c["due_at"] <= now
        wrong = any(not g["correct"] for g in answers)
        for g in answers:
            c["p_mastery"] = bkt(c["p_mastery"], g["correct"], confidence.get(g["question_id"]))
            c["attempts"] += 1
        if was_m and wrong:
            c["stability_days"] = max(1.0, c["stability_days"] / 2)
            c["p_mastery"] = min(c["p_mastery"], 0.5)
            c["lapses"] += 1
            events[cid] = "lapse"
        elif was_due and not wrong:
            c["stability_days"] = max(1.0, c["stability_days"]) * 2.5
            events[cid] = "review success"
        elif not was_m and c["p_mastery"] >= THR:
            c["stability_days"] = 1.0
            events[cid] = "first mastery"
    if diagnostic:
        for cid, answers in by.items():
            if all(g["correct"] for g in answers):
                c = concepts[cid]
                c["p_mastery"] = THR
                c["stability_days"] = min(PLACE_DAYS.get(confidence.get(g["question_id"]) or "low", 1.0)
                                          for g in answers)
                events[cid] = f"placed ({c['stability_days']:g} d)"
    return {"concepts": concepts, "events": events, "diagnostic": diagnostic}


def predict_step(state: dict, graph: list[dict], now: datetime) -> tuple[str, str | None, str]:
    """What the policy should pick, re-derived from the documented rules."""
    cs = state["concepts"]
    get = lambda cid: cs.get(cid) or {"p_mastery": 0.2, "stability_days": 0, "lapses": 0, "failed_rounds": 0,  # noqa: E731
                                      "needs_help": False, "last_reviewed_at": None, "due_at": None, "fallbacks": 0}
    unlocked = lambda c: all(get(p)["p_mastery"] >= THR for p in c["prerequisites"])  # noqa: E731
    prio = lambda c: get(c["id"])["p_mastery"] * retrievability(get(c["id"]), now)  # noqa: E731
    if state["session_questions"] >= SESSION_CAP:
        return "session_end", None, "session cap reached"

    def lesson(c, why):
        x = get(c["id"])
        if x["failed_rounds"] >= ROUND_CAP:
            if c["prerequisites"] and x.get("fallbacks", 0) == 0:
                return "fallback", None, f"{c['id']} stuck: fallback to a prerequisite"
            return "lesson", c["id"], f"{c['id']} stuck: last try"
        return "lesson", c["id"], why

    relearn = [c for c in graph if (get(c["id"])["stability_days"] > 0 or get(c["id"])["lapses"] > 0)
               and get(c["id"])["p_mastery"] < THR and get(c["id"])["failed_rounds"] > 0
               and not get(c["id"]).get("needs_help") and unlocked(c)]
    if relearn:
        return lesson(min(relearn, key=prio), "relearn first: mastered before, slipped and failed since")
    due = [cid for cid in state["roadmap"] if get(cid).get("due_at") and get(cid)["due_at"] <= now]
    if due:
        cid = min(due, key=lambda x: retrievability(get(x), now))
        return "review", cid, "due review with the lowest retrievability"
    cands = [c for c in graph if get(c["id"])["p_mastery"] < THR and not get(c["id"]).get("needs_help") and unlocked(c)]
    if not cands:
        return "done", None, "nothing unmastered is unlocked"
    return lesson(min(cands, key=prio), "lowest p x retrievability among unlocked, unmastered concepts")


# --- trace document ---

class Trace:
    def __init__(self) -> None:
        self.started = datetime.now()
        self.t0 = time.monotonic()
        self.steps: list[dict] = []
        self.problems: list[str] = []
        self.not_verified: list[str] = []
        self.notes: list[str] = []
        self.verdict = "running"
        self.concepts: list[str] = []
        DOCS.mkdir(exist_ok=True)

    def problem(self, text: str) -> None:
        self.problems.append(text)
        print(f"  !! {text}")

    def unverified(self, text: str) -> None:
        if text not in self.not_verified:
            self.not_verified.append(text)

    def totals(self) -> dict:
        llm = [c for s in self.steps for c in s.get("external", {}).get("llm", [])]
        return {"calls": len(llm), "in": sum(c["in"] for c in llm), "out": sum(c["out"] for c in llm),
                "usd": sum(c["usd"] for c in llm)}

    def render(self) -> str:
        t = self.totals()
        out = [f"# OnlyNerd trace: {TOPIC} ({LEVEL})", "",
               f"- Date: {self.started:%Y-%m-%d %H:%M:%S}",
               f"- Python {platform.python_version()}; " + ", ".join(
                   f"{p} {_version(p)}" for p in ("fastapi", "pydantic", "pymongo", "langchain-anthropic")),
               f"- Total elapsed: {time.monotonic() - self.t0:.1f} s",
               f"- LLM (server, from its log): {t['calls']} calls, {t['in']} input + {t['out']} output tokens, "
               f"estimated ${t['usd']:.4f}",
               f"- Verdict: **{self.verdict}**", ""]
        out += [f"- {n}" for n in self.notes]
        out += ["", "## Contents", ""]
        out += [f"{s['n']}. [{s['title']}](#step-{s['n']}) - {s.get('status', 'running')}" for s in self.steps]
        for s in self.steps:
            out += render_step(s)
        out += render_trajectories(self)
        out += ["", "## Problems found", ""] + ([f"- {p}" for p in self.problems] or ["_(none)_"])
        out += ["", "## Not verified", ""] + ([f"- {p}" for p in self.not_verified] or ["_(none)_"])
        return scrub("\n".join(out) + "\n")

    def save(self) -> None:
        raw = {"started": self.started, "notes": self.notes, "steps": self.steps, "problems": self.problems,
               "not_verified": self.not_verified, "verdict": self.verdict, "totals": self.totals()}
        for path, text in ((MD_PATH, self.render()), (JSON_PATH, scrub(json.dumps(raw, indent=2, default=str)))):
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, path)


def _version(pkg: str) -> str:
    try:
        return md.version(pkg)
    except md.PackageNotFoundError:
        return "not installed"


def code_block(text: str, lang: str = "") -> list[str]:
    return [f"```{lang}", text, "```"]


def render_step(s: dict) -> list[str]:
    out = ["", f"<a id=\"step-{s['n']}\"></a>", f"## {s['n']}. {s['title']}", "", f"**a. What and why.** {s['why']}", ""]
    for i, call in enumerate(s.get("calls", [])):
        req = call["request"]
        label = f" (request {i + 1})" if len(s["calls"]) > 1 else ""
        out += [f"**b. Request{label}**", "", f"`{req['method']} {req['url']}`", "",
                *code_block(json.dumps(req["headers"], indent=2), "json")]
        if req.get("json") is not None:
            out += code_block(json.dumps(req["json"], indent=2), "json")
        else:
            out += ["(no body)"]
        resp = call.get("response")
        out += ["", f"**c. Response{label}**", ""]
        if resp is None:
            out += [f"error: {call.get('error')}"]
        else:
            body = json.dumps(resp["json"], indent=2) if resp["json"] is not None else resp["text"]
            if len(body) > TRUNCATE:
                body = body[:TRUNCATE] + f"\n[truncated, {len(body)} chars]"
            out += [f"status {resp['status']}, {resp['ms']:.0f} ms", "", *code_block(body, "json")]
        for p in call.get("polls", []):
            out.append(f"- poll: {p}")
        out.append("")
    ext = s.get("external")
    out += ["**d. External calls**", ""]
    if ext is None:
        out.append("(not captured)")
    elif not (ext["llm"] or ext["tavily"] or ext["youtube"] or ext["retries"] or ext["warnings"]):
        out.append("none" + (f" ({ext['anthropic_http']} Anthropic HTTP requests logged)" if ext["anthropic_http"] else ""))
    else:
        if ext["llm"]:
            out += ["| role | model | input | output | est. USD |", "|---|---|---|---|---|"]
            out += [f"| {c['role']} | {c['model']} | {c['in']} | {c['out']} | {c['usd']:.5f} |" for c in ext["llm"]]
            out += [f"", f"{len(ext['llm'])} LLM calls, ${sum(c['usd'] for c in ext['llm']):.5f}; "
                    f"{ext['anthropic_http']} Anthropic HTTP requests in the log"]
        else:
            out.append("LLM: none")
        out.append(f"Tavily: {len(ext['tavily'])} log lines; YouTube: {len(ext['youtube'])} log lines")
        for k in ("tavily", "youtube", "retries", "warnings"):
            out += [f"- {k}: `{ln[:300]}`" for ln in ext[k]]
    out += ["", "**e. Internal state (Mongo)**", ""]
    st = s.get("state")
    if st is None:
        out.append("(no learner state yet)")
    else:
        cols = ["p_mastery", "attempts", "failed_rounds", "stability_days", "last_reviewed_at", "due_at",
                "lapses", "fallbacks", "needs_help", "explanations_tried"]
        out += ["| concept | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
        for cid in st["roadmap"]:
            c = st["concepts"].get(cid, {})
            out.append(f"| {cid} | " + " | ".join(fmt(c.get(k)) for k in cols) + " |")
        out += ["", "Misconceptions:", ""]
        if st["misconceptions"]:
            out += ["| tag | status | evidence | clean_streak |", "|---|---|---|---|"]
            out += [f"| {t} | {m['status']} | {m['evidence']:g} | {m['clean_streak']} |"
                    for t, m in st["misconceptions"].items()]
        else:
            out.append("none")
        out += ["", f"session_questions: {st['session_questions']}; clock_offset_days: {st['clock_offset_days']:g}",
                f"roadmap: {st['roadmap']}",
                f"history: {st.get('history_note')}",
                f"lesson cache keys ({len(s.get('lesson_keys', []))}): "
                + (", ".join(f"`{k[:12]}` ({c}, {sty})" for k, c, sty in s.get("lesson_keys", [])) or "none")]
    out += ["", "**f. What changed**", ""]
    out += [f"- {d}" for d in s.get("diff", [])] or ["nothing"]
    out += ["", "**g. Independent check**", ""]
    if s.get("checks"):
        out += ["| quantity | expected | actual | result |", "|---|---|---|---|"]
        out += [f"| {c['what']} | {c['expected']} | {c['actual']} | {'OK' if c['ok'] else 'MISMATCH'} |"
                for c in s["checks"]]
    else:
        out.append(s.get("check_note", "nothing to recompute in this step"))
    out += ["", "**h. Brain decision**", "", s.get("brain", "no brain decision in this step")]
    if s.get("extra"):
        out += ["", *s["extra"]]
    return out


def render_trajectories(tr: Trace) -> list[str]:
    rows = [s for s in tr.steps if s.get("state")]
    if not rows:
        return []
    cids = rows[-1]["state"]["roadmap"]
    out = ["", "## Trajectories", ""]
    for title, key in (("p_mastery after each step", "p"), ("retrievability (at the step's simulated now)", "r"),
                       ("stability_days", "s")):
        out += [f"### {title}", "", "| step | " + " | ".join(cids) + " |", "|---" * (len(cids) + 1) + "|"]
        for s in rows:
            vals = s["traj"][key]
            out.append(f"| {s['n']} | " + " | ".join(f"{vals.get(c, 0):.3f}" for c in cids) + " |")
        out.append("")
    return out


# --- runner ---

TR = Trace()
SRV = Server()
mongo = MongoClient(SETTINGS.MONGO_URI)[SETTINGS.MONGO_DB]
HEADERS_SHOWN = {"X-Master-Password": "***", "Content-Type": "application/json"}
CTX: dict = {"cid": None, "prev_state": None, "pending": None, "graph": [], "bundle": None}


def read_state() -> dict | None:
    doc = mongo.learner_states.find_one({"_id": f"{LEARNER}:{CTX['cid']}"}) if CTX["cid"] else None
    if doc is None:
        return None
    doc.pop("_id", None)
    doc["history_note"] = (f"{len(doc['history'])} points, last {doc['history'][-1]}" if doc.get("history")
                           else "no history field in the stored state")
    return doc


def lesson_keys() -> list[tuple[str, str, str]]:
    ids = {c["id"] for c in CTX["graph"]}
    return [(d["_id"], d["concept_id"], d.get("style")) for d in mongo.lessons.find({"concept_id": {"$in": list(ids)}})]


def flatten(st: dict | None) -> dict:
    if not st:
        return {}
    flat = {"session_questions": st["session_questions"], "clock_offset_days": st["clock_offset_days"],
            "roadmap": st["roadmap"]}
    for cid, c in st["concepts"].items():
        for k, v in c.items():
            if k != "concept_id":
                flat[f"concepts.{cid}.{k}"] = v
    for t, m in st["misconceptions"].items():
        for k, v in m.items():
            if k not in ("tag", "concept_id"):
                flat[f"misconceptions.{t}.{k}"] = v
    return flat


def diff(before: dict | None, after: dict | None) -> list[str]:
    a, b = flatten(before), flatten(after)
    return [f"{k}: {fmt(a.get(k, '(absent)'))} -> {fmt(b.get(k, '(absent)'))}"
            for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]


def sim_now(state: dict | None, real: datetime) -> datetime:
    return real + timedelta(days=state["clock_offset_days"] if state else 0)


def leak_check(n: int, body) -> None:
    def walk(x):
        if isinstance(x, dict):
            if "questions" in x and isinstance(x["questions"], list):
                for q in x["questions"]:
                    if isinstance(q, dict) and set(q) - {"id", "concept_id", "prompt", "options"}:
                        TR.problem(f"step {n}: question {q.get('id')} leaks hidden fields "
                                   f"{sorted(set(q) - {'id', 'concept_id', 'prompt', 'options'})} before grading")
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(body)


def request(client: httpx.Client, step: dict, method: str, path: str, body=None, expect_ok=True) -> dict | None:
    call = {"request": {"method": method, "url": f"{BASE}{path}", "headers": HEADERS_SHOWN, "json": body}}
    step.setdefault("calls", []).append(call)
    t0 = time.monotonic()
    try:
        r = client.request(method, path, json=body)
    except httpx.HTTPError as exc:
        call["error"] = f"{type(exc).__name__}: {exc}"
        raise
    ms = (time.monotonic() - t0) * 1000
    try:
        data = r.json()
    except ValueError:
        data = None
    call["response"] = {"status": r.status_code, "ms": ms, "json": data, "text": scrub(r.text[:2000])}
    step["secs"] = step.get("secs", 0) + ms / 1000
    leak_check(step["n"], data)
    if expect_ok and r.status_code >= 400:
        raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:300]}")
    return data


def run_step(client: httpx.Client, n: int, title: str, why: str, fn) -> None:
    step = {"n": n, "title": title, "why": why, "status": "running"}
    TR.steps.append(step)
    print(f"\n=== step {n}: {title}")
    before = CTX["prev_state"]
    t0, real0 = time.monotonic(), utcnow()
    try:
        fn(client, step)
        step["status"] = "ok"
    except Exception as exc:  # noqa: BLE001
        step["status"] = f"FAILED: {type(exc).__name__}: {exc}"
        TR.problem(f"step {n} ({title}) failed: {type(exc).__name__}: {exc}")
        raise
    finally:
        t1 = time.monotonic()
        step["external"] = external_calls(SRV.window(t0, t1))
        for w in step["external"]["warnings"]:
            TR.problem(f"step {n}: server log: {w[:300]}")
        after = read_state()
        step["state"], step["lesson_keys"] = after, lesson_keys()
        step["diff"] = diff(before, after)
        if after:
            now = sim_now(after, real0)
            step["traj"] = {"p": {c: v["p_mastery"] for c, v in after["concepts"].items()},
                            "r": {c: retrievability(v, now) for c, v in after["concepts"].items()},
                            "s": {c: v["stability_days"] for c, v in after["concepts"].items()}}
        if step.get("secs", 0) > SLOW_SECONDS and n != 2:
            TR.problem(f"step {n} ({title}) took {step['secs']:.1f} s (over {SLOW_SECONDS} s)")
        CTX["prev_state"] = after
        print(f"  {step['status']} ({step.get('secs', 0):.2f} s request time)")
        TR.save()


def add_check(step: dict, what: str, expected, actual, ok: bool) -> None:
    step.setdefault("checks", []).append({"what": what, "expected": fmt(expected), "actual": fmt(actual), "ok": ok})
    if not ok:
        TR.problem(f"step {step['n']}: MISMATCH {what}: expected {fmt(expected)}, actual {fmt(actual)}")


def close(a, b, tol) -> bool:
    return a is not None and b is not None and math.isclose(a, b, rel_tol=0, abs_tol=tol)


# --- attempts with checks ---

def submit(client, step, answers: list[dict]) -> dict:
    prev = deepcopy(CTX["prev_state"])
    real = utcnow()
    res = request(client, step, "POST", f"/courses/{CTX['cid']}/learners/{LEARNER}/attempts", {"answers": answers})
    after = read_state()
    now = sim_now(after, real)
    conf = {a["question_id"]: a.get("confidence") for a in answers}
    exp = expected_round(prev, res["graded"], conf, now)
    key = {q.id: q for q in CTX["bundle"].questions}
    for g in res["graded"]:
        q = key[g["question_id"]]
        chosen = next(a["chosen_index"] for a in answers if a["question_id"] == g["question_id"])
        add_check(step, f"{g['question_id']} correct", chosen == q.correct_index, g["correct"],
                  (chosen == q.correct_index) == g["correct"])
        if not g["correct"]:
            add_check(step, f"{g['question_id']} chosen_tag", q.options[chosen].misconception_tag, g["chosen_tag"],
                      q.options[chosen].misconception_tag == g["chosen_tag"])
    for cid in exp["concepts"]:
        e, a = exp["concepts"][cid], after["concepts"][cid]
        if cid not in {g["concept_id"] for g in res["graded"]}:
            continue
        add_check(step, f"{cid} p_mastery ({exp['events'].get(cid, 'BKT only')})", e["p_mastery"], a["p_mastery"],
                  close(e["p_mastery"], a["p_mastery"], TOL_P))
        add_check(step, f"{cid} stability_days", e["stability_days"], a["stability_days"],
                  close(e["stability_days"], a["stability_days"], TOL_P))
        add_check(step, f"{cid} lapses", e["lapses"], a["lapses"], e["lapses"] == a["lapses"])
        if cid in exp["events"]:
            gap = (a["due_at"] - a["last_reviewed_at"]).total_seconds() / 86400 if a["due_at"] else None
            add_check(step, f"{cid} due_at - last_reviewed_at (days)", e["stability_days"], gap,
                      close(e["stability_days"], gap, 1e-6))
        add_check(step, f"{cid} mastery in response = Mongo", a["p_mastery"], res["mastery"][cid],
                  close(a["p_mastery"], res["mastery"][cid], TOL_P))
    if exp["diagnostic"]:
        add_check(step, "session_questions after the diagnostic", 0, after["session_questions"],
                  after["session_questions"] == 0)
    nxt = res["next"]
    kind, cid, why = predict_step(after, CTX["graph"], now)
    match = (kind, cid) == (nxt["step"]["kind"], nxt["step"]["concept_id"]) or (kind == "fallback" == nxt["step"]["kind"])
    step["brain"] = (f"Reason: \"{nxt['reason']}\"\n\nThe brain chose **{nxt['step']['kind']} "
                     f"{nxt['step']['concept_id'] or ''}**. Re-derived from the rules: {kind} {cid or ''} ({why}): "
                     f"{'as expected' if match else 'DIFFERENT from what the rules predict'}.")
    if not match:
        TR.problem(f"step {step['n']}: brain chose {nxt['step']['kind']} {nxt['step']['concept_id']}, rules predict {kind} {cid}")
    if not nxt["reason"].strip():
        TR.problem(f"step {step['n']}: empty reason on the next step")
    if nxt["step"]["kind"] in ("lesson", "fallback") and not nxt.get("lesson"):
        TR.problem(f"step {step['n']}: lesson step came without a lesson")
    if nxt.get("lesson") is not None and not nxt["lesson"]["resources"]:
        TR.problem(f"step {step['n']}: lesson has no resources (get_resources is a stub)")
    CTX["pending"] = nxt
    return res


def answer(q_id: str, correct: bool, confidence: str | None) -> dict:
    q = next(q for q in CTX["bundle"].questions if q.id == q_id)
    idx = q.correct_index if correct else next(i for i, o in enumerate(q.options) if o.misconception_tag)
    return {"question_id": q_id, "chosen_index": idx, "confidence": confidence}


def served_review(client, step) -> tuple[str, list[str]]:
    """GET .../next: the review the brain decided at advance time, with the questions the server serves."""
    first = request(client, step, "GET", f"/courses/{CTX['cid']}/learners/{LEARNER}/next")
    again = request(client, step, "GET", f"/courses/{CTX['cid']}/learners/{LEARNER}/next")
    add_check(step, "GET /next twice returns the same step and questions", "identical",
              "identical" if first == again else "different", first == again)
    st = read_state()
    kind, cid, why = predict_step(st, CTX["graph"], sim_now(st, utcnow()))
    if first["step"]["kind"] != "review":
        raise RuntimeError(f"GET /next returned {first['step']['kind']}, expected a review")
    ids = [q["id"] for q in first["questions"]]
    add_check(step, "served_question_ids = the /next questions", ids, st["served_question_ids"],
              ids == st["served_question_ids"])
    step.setdefault("extra", []).append(
        f"GET /next served **{first['step']['kind']} {first['step']['concept_id']}** "
        f"(reason: \"{first['reason']}\") with questions {ids}.")
    return first["step"]["concept_id"], ids


def state_checks(client, step):
    real = utcnow()
    s = request(client, step, "GET", f"/courses/{CTX['cid']}/learners/{LEARNER}/state")
    st = read_state()
    now = sim_now(st, real)
    for c in s["concepts"]:
        cid = c["concept_id"]
        exp_r = retrievability(st["concepts"][cid], now)
        add_check(step, f"{cid} retrievability 0.9^(t/S)", round(exp_r, 4), round(s["retrievability"][cid], 4),
                  close(exp_r, s["retrievability"][cid], TOL_R))
    due_exp = {cid: c["due_at"] for cid, c in st["concepts"].items() if c.get("due_at")}
    add_check(step, "due (concepts with a schedule)", sorted(due_exp), sorted(s["due"]), sorted(due_exp) == sorted(s["due"]))
    gaps = [c for c in st["roadmap"] if st["concepts"][c]["p_mastery"] < THR]
    add_check(step, "gaps", gaps, s["gaps"], gaps == s["gaps"])
    step["check_note"] = ""
    step["brain"] = "No brain decision in this step (state read only)."
    return s


# --- the steps ---

def s1(client, step):
    request(client, step, "GET", "/health")


def s2(client, step):
    h = prompt_hash(TOPIC, LEVEL)
    in_mongo = mongo.courses.find_one({"prompt_hash": h, "level": LEVEL, "status": {"$ne": "failed"}})
    in_cache = (ROOT / ".cache" / f"{h}.json").exists()
    TR.notes.append(f"Course for '{TOPIC}' ({LEVEL}), prompt hash {h}: "
                    f"{'already in Mongo (' + in_mongo['_id'] + ', ' + in_mongo['status'] + ')' if in_mongo else 'not in Mongo'}; "
                    f"{'cached bundle in .cache/' if in_cache else 'no cached bundle'}.")
    body = request(client, step, "POST", "/courses", {"prompt": TOPIC, "level": LEVEL})
    CTX["cid"] = body["course_id"]
    t0 = time.monotonic()
    polls = step["calls"][-1].setdefault("polls", [])
    while body["status"] == "generating":
        if time.monotonic() - t0 > GEN_TIMEOUT:
            raise TimeoutError("course still generating after 8 minutes")
        time.sleep(3)
        r = client.get(f"/courses/{CTX['cid']}")
        body = r.json()
        polls.append(f"GET /courses/{CTX['cid']} -> {r.status_code} status={body['status']} at {time.monotonic() - t0:.0f} s")
        TR.save()
    skipped = not polls
    TR.notes.append(f"Generation {'skipped: the course was ready at once (reused)' if skipped else f'ran: ready after {time.monotonic() - t0:.0f} s'}.")
    if body["status"] != "ready":
        raise RuntimeError(f"course status {body['status']}")
    CTX["bundle"] = find_bundle(TOPIC, LEVEL)
    if CTX["bundle"] is None:
        raise RuntimeError("no cached bundle for the answer key")
    # A deterministic trace needs a fresh learner: remove this script's earlier 'trace' learner.
    gone_s = mongo.learner_states.delete_one({"_id": f"{LEARNER}:{CTX['cid']}"}).deleted_count
    gone_a = mongo.attempts.delete_many({"learner_id": LEARNER, "course_id": CTX["cid"]}).deleted_count
    if gone_s or gone_a:
        TR.notes.append(f"Reset learner '{LEARNER}' from an earlier trace: deleted {gone_s} state and {gone_a} attempt documents.")
    step["brain"] = "No brain decision (course creation)."


def s3(client, step):
    body = request(client, step, "GET", f"/courses/{CTX['cid']}")
    CTX["graph"] = body["concepts"]
    roots = [c["id"] for c in body["concepts"] if not c["prerequisites"]]
    step["extra"] = [f"{len(body['concepts'])} concepts, roots {roots}; {len(CTX['bundle'].questions)} questions in the cached bundle."]


def s4(client, step):
    body = request(client, step, "POST", f"/courses/{CTX['cid']}/learners/{LEARNER}/start")
    CTX["diag"] = body["questions"]
    st = read_state()
    order = [q["concept_id"] for q in body["questions"]]
    add_check(step, "diagnostic order = roadmap", st["roadmap"], order, st["roadmap"] == order)
    add_check(step, "every concept starts at p=0.2", 0.2, sorted({c["p_mastery"] for c in st["concepts"].values()}),
              all(c["p_mastery"] == 0.2 for c in st["concepts"].values()))


def s5(client, step):
    plan = []
    for i, q in enumerate(CTX["diag"], start=1):
        if i <= 3:
            plan.append(answer(q["id"], True, "medium"))
        elif i == 4:
            plan.append(answer(q["id"], False, "high"))
        elif i == 5:
            plan.append(answer(q["id"], True, "low"))
        elif i == 6:
            plan.append(answer(q["id"], False, "low"))
        else:
            plan.append(answer(q["id"], True, "high"))
    submit(client, step, plan)


def s7(client, step):
    qs = CTX["pending"]["questions"]
    if len(qs) < 3:
        raise RuntimeError(f"expected 3 practice questions, got {len(qs)}")
    submit(client, step, [answer(qs[0]["id"], True, "medium"), answer(qs[1]["id"], True, "medium"),
                          answer(qs[2]["id"], False, "medium")])


def advance(days):
    def fn(client, step):
        before = CTX["prev_state"]["clock_offset_days"]
        body = request(client, step, "POST", f"/courses/{CTX['cid']}/learners/{LEARNER}/advance", {"days": days})
        st = read_state()
        add_check(step, "clock_offset_days", before + days, st["clock_offset_days"], st["clock_offset_days"] == before + days)
        add_check(step, "session_questions reset", 0, st["session_questions"], st["session_questions"] == 0)
        now = datetime.fromisoformat(body["now"])
        due = sorted(c for c, v in st["concepts"].items() if v.get("due_at") and v["due_at"] <= now)
        add_check(step, "due_now = concepts with due_at <= now", due, sorted(body["due_now"]), due == sorted(body["due_now"]))
        kind, cid, why = predict_step(st, CTX["graph"], now)
        got = (body.get("next_kind"), body.get("next_concept_id"))
        match = got == (kind, cid) or (kind == "fallback" == got[0])
        step["brain"] = (f"advance stored the decision **{got[0]} {got[1] or ''}** (served later by GET /next). "
                         f"Re-derived from the rules: {kind} {cid or ''} ({why}): "
                         f"{'as expected' if match else 'DIFFERENT from what the rules predict'}.")
        if not match:
            TR.problem(f"step {step['n']}: advance decided {got}, rules predict {(kind, cid)}")
    return fn


def s11(client, step):
    _, ids = served_review(client, step)
    submit(client, step, [answer(q, True, "medium") for q in ids])


def s14(client, step):
    _, ids = served_review(client, step)
    submit(client, step, [answer(q, False, "high") for q in ids])


def s15(client, step):
    state_checks(client, step)
    nxt = CTX["pending"]
    served = request(client, step, "GET", f"/courses/{CTX['cid']}/learners/{LEARNER}/next")
    same = served["step"] == nxt["step"] and [q["id"] for q in served["questions"]] == [q["id"] for q in nxt["questions"]]
    add_check(step, "GET /next = the step returned by step 14", "same step and questions",
              "same" if same else "different", same)
    lines = [f"Next step from step 14's response: **{nxt['step']['kind']} {nxt['step']['concept_id'] or ''}**",
             f"", f"Reason: \"{nxt['reason']}\"", f"", f"Step: `{json.dumps(nxt['step'])}`"]
    if nxt.get("lesson"):
        les = nxt["lesson"]
        lines += ["", f"Lesson style **{les['style']}**, targets {les['targets']}, {len(les['explanation'].split())} words, "
                  f"{len(les['resources'])} resources:", "", *[f"> {p}" for p in les["explanation"].split("\n")]]
    lines += ["", "Questions:"]
    for q in nxt["questions"]:
        lines += [f"- [{q['id']}] {q['prompt']}", *[f"  {i}. {o}" for i, o in enumerate(q["options"])]]
    step["extra"] = lines
    if nxt["step"]["kind"] != "lesson":
        TR.problem(f"step 15: expected a relearn lesson after the failed review, got {nxt['step']['kind']}")


def s16(client, step):
    request(client, step, "POST", f"/courses/{CTX['cid']}/learners/{LEARNER}/sessions/new")
    st = read_state()
    add_check(step, "session_questions", 0, st["session_questions"], st["session_questions"] == 0)


def s17(client, step):
    codes = []
    for path in (f"/courses/{CTX['cid']}/learners/{LEARNER}/resources",
                 f"/courses/{CTX['cid']}/learners/{LEARNER}/virtual/status", "/eval/results"):
        request(client, step, "GET", path, expect_ok=False)
        codes.append((path, step["calls"][-1]["response"]["status"]))
    step["extra"] = [f"- `{p}` -> {c}" for p, c in codes]
    add_check(step, "/eval/results status", 404, codes[2][1], codes[2][1] == 404)
    for p, c in codes[:2]:
        if c == 404:
            TR.unverified(f"`{p.split(LEARNER)[-1]}`: the route does not exist yet (404).")
    step["brain"] = "No brain decision."


STEPS = [
    (1, "GET /health", "Confirm the server this script launched is up before tracing anything.", s1),
    (2, "POST /courses", "Create (or reuse) the course for the topic; generation runs in the background, so poll until it is ready.", s2),
    (3, "GET /courses/{cid}", "Read the course as the UI sees it: topic and the concept graph with prerequisites.", s3),
    (4, "POST .../start", "Create the learner 'trace' with every concept at the prior and get one diagnostic question per concept, without answers.", s4),
    (5, "POST .../attempts (diagnostic)", "Answer the diagnostic with a fixed script (right/wrong and confidence per concept) to exercise BKT, misconception evidence and placement.", s5),
    (6, "GET .../state", "Read the dashboard numbers after the diagnostic and check retrievability, due dates and gaps.", lambda c, s: state_checks(c, s)),
    (7, "POST .../attempts (practice)", "Answer the 3 practice questions of the step the brain returned: 2 right, 1 wrong with a tag.", s7),
    (8, "GET .../state", "Read the state after the practice round.", lambda c, s: state_checks(c, s)),
    (9, "POST .../advance {days: 1}", "Move the learner's clock 1 day: low-confidence placements become due.", advance(1)),
    (10, "GET .../state", "Read the state 1 day later: retrievability falls, due reviews appear.", lambda c, s: state_checks(c, s)),
    (11, "GET .../next + POST .../attempts (review, right)", "Fetch the review the brain stored at advance time (twice, to show it is idempotent) and pass it: stability should grow 2.5x.", s11),
    (12, "POST .../advance {days: 3}", "Move the clock 3 more days so more placed concepts fall due.", advance(3)),
    (13, "GET .../state", "Read the state 4 days in.", lambda c, s: state_checks(c, s)),
    (14, "GET .../next + POST .../attempts (review, wrong)", "Fetch the stored review and fail it on purpose (all wrong, high confidence): a lapse.", s14),
    (15, "GET .../state + GET .../next (relearn lesson)", "Read the state after the lapse and show the relearn lesson, also served by GET /next.", s15),
    (16, "POST .../sessions/new", "Start a new session: the session counter resets.", s16),
    (17, "Unwired and eval routes", "Probe the research, virtual-learner and eval routes and record their status codes.", s17),
]


def main() -> int:
    TR.unverified("Log attribution is by arrival time of each server log line between request start and end; "
                  "background work (e.g. generation) logged during another request would be attributed to it.")
    TR.unverified("Simulated 'now' is approximated in the script as real UTC at request start plus the offset; "
                  "comparisons use a 0.001 tolerance on retrievability.")
    TR.save()
    SRV.start()
    print(f"server pid {SRV.proc.pid}; document: {MD_PATH}")
    headers = {"X-Master-Password": PASSWORD}
    try:
        for _ in range(60):
            try:
                if httpx.get(f"{BASE}/health", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.5)
        with httpx.Client(base_url=BASE, headers=headers, timeout=300) as client:
            for n, title, why, fn in STEPS:
                run_step(client, n, title, why, fn)
        TR.verdict = "passed" if not TR.problems else f"completed with {len(TR.problems)} problem(s)"
        return 0
    except Exception as exc:  # noqa: BLE001
        TR.verdict = f"FAILED at step {len(TR.steps)}: {type(exc).__name__}: {exc}"
        print(f"\n!! {TR.verdict}")
        return 1
    finally:
        SRV.stop()
        TR.save()
        t = TR.totals()
        print(f"\nverdict: {TR.verdict}")
        print(f"LLM (server): {t['calls']} calls, {t['in']} in + {t['out']} out tokens, ${t['usd']:.4f}")
        print(f"problems: {len(TR.problems)}\ndocument: {MD_PATH}\nraw: {JSON_PATH}")


if __name__ == "__main__":
    sys.exit(main())
