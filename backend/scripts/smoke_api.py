"""End-to-end check against a running server (uv run uvicorn main:app).

Creates the course from a fixture bundle and runs three fresh learners on it:
  main:      diagnostic right on the first 3 concepts (placed as known), wrong on the rest; master
             the first lesson's concept; advance 3 days; reviews are due and retrievability dropped.
  all right: every concept placed, nothing left to learn; after 1 day every concept is due.
  all wrong: every concept is a gap; the next step is a lesson on a root concept.
Concept ids come from the fixture's graph.

Usage: uv run python scripts/smoke_api.py [--base http://127.0.0.1:8000] [--fixture fixtures/x.json]
The X-Master-Password header comes from MASTER_PASSWORD in the environment or .env.
"""

import argparse
import json
import sys
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import get_settings  # noqa: E402
from schemas.content import Question  # noqa: E402

FIXTURES = ROOT / "fixtures"


def default_fixture() -> Path:
    preferred = FIXTURES / "python_novice.json"
    if preferred.exists():
        return preferred
    found = sorted(FIXTURES.glob("*.json"))
    if not found:
        sys.exit("no fixtures/*.json")
    return found[0]


def check(cond: bool, what: str) -> None:
    print(f"  [{'ok' if cond else 'FAIL'}] {what}")
    if not cond:
        sys.exit(1)


def call(c: httpx.Client, method: str, path: str, **kw) -> dict:
    r = c.request(method, path, **kw)
    if r.status_code >= 400:
        print(f"{method} {path} -> {r.status_code}: {r.text}")
        sys.exit(1)
    return r.json()


class Run:
    """One fresh learner on the course."""

    def __init__(self, c: httpx.Client, cid: str, key: dict[str, Question], label: str):
        self.c, self.key = c, key
        self.lid = f"smoke-{label}-{uuid.uuid4().hex[:6]}"
        self.base = f"/courses/{cid}/learners/{self.lid}"
        print(f"\n== {label}: learner {self.lid}")

    def start(self) -> list[dict]:
        diag = call(self.c, "POST", f"{self.base}/start")["questions"]
        print(f"diagnostic: {len(diag)} questions, concepts {[q['concept_id'] for q in diag]}")
        return diag

    def answer(self, questions: list[dict], right: set[str], confidence: str | None = None) -> dict:
        answers = []
        for q in questions:
            k = self.key[q["id"]]
            wrong = next(i for i in range(len(k.options)) if i != k.correct_index)
            answers.append({"question_id": q["id"], "confidence": confidence,
                            "chosen_index": k.correct_index if q["concept_id"] in right else wrong})
        res = call(self.c, "POST", f"{self.base}/attempts", json={"answers": answers})
        step = res["next"]
        print("messages:", res["messages"])
        print(f"next: {step['step']['kind']} {step['step']['concept_id']} | reason: {step['reason']}")
        print(f"  lesson: {(step['lesson'] or {}).get('style')} | questions: {[q['id'] for q in step['questions']]}")
        return res

    def state(self) -> dict:
        return call(self.c, "GET", f"{self.base}/state")

    def advance(self, days: int) -> dict:
        adv = call(self.c, "POST", f"{self.base}/advance", json={"days": days})
        print(f"advance {days}: now={adv['now']} due_now={adv['due_now']}")
        return adv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--fixture", type=Path, default=None)
    args = parser.parse_args()

    fixture = args.fixture or default_fixture()
    bundle = json.loads(fixture.read_text(encoding="utf-8"))
    key = {q["id"]: Question.model_validate(q) for q in bundle["questions"]}
    roots = {c["id"] for c in bundle["graph"]["concepts"] if not c["prerequisites"]}
    password = get_settings().MASTER_PASSWORD.get_secret_value()
    headers = {"X-Master-Password": password} if password else {}
    print(f"fixture {fixture.name}: prompt={bundle['prompt']!r} level={bundle['level']} "
          f"{len(bundle['graph']['concepts'])} concepts, {len(key)} questions")

    with httpx.Client(base_url=args.base, headers=headers, timeout=180) as c:
        print("health:", httpx.get(f"{args.base}/health").json())
        if password:
            r = httpx.post(f"{args.base}/courses", json={"prompt": "x"})
            check(r.status_code == 401, f"no password -> {r.status_code}")

        course = call(c, "POST", "/courses", json={"prompt": bundle["prompt"], "level": bundle["level"]})
        cid = course["course_id"]
        print(f"course {cid}: status={course['status']} topic={course['topic']!r}")
        check(course["status"] == "ready", "fixture course is ready at once")
        all_ids = {x["id"] for x in course["concepts"]}
        check(all_ids == {x["id"] for x in bundle["graph"]["concepts"]}, "course concepts match the fixture graph")

        # --- main run ---
        run = Run(c, cid, key, "main")
        diag = run.start()
        check(all(set(q) == {"id", "concept_id", "prompt", "options"} for q in diag),
              "diagnostic hides correct_index, tags and explanations")
        check({q["concept_id"] for q in diag} == all_ids, "one diagnostic question per concept")
        right = {q["concept_id"] for q in diag[:3]}
        res = run.answer(diag, right, confidence="high")
        step = res["next"]
        print("mastery:", {k: round(v, 3) for k, v in res["mastery"].items()})
        print("new confirmed:", res["new_confirmed_misconceptions"])
        check([g["correct"] for g in res["graded"]] == [q["concept_id"] in right for q in diag], "grading matches script")
        check(all(res["mastery"][x] == 0.85 for x in right), "right concepts placed at 0.85")
        check("Placed 3 concepts as already known; I'll check them again tomorrow." in res["messages"],
              "placement message")
        check(step["reason"].startswith("placed as known:"), "placement in the step reason")
        check(step["step"]["kind"] == "lesson" and step["step"]["concept_id"] not in right,
              "next step is a lesson on an unplaced concept")
        check(len(step["questions"]) == 3 and all(key[q["id"]].kind != "diagnostic" for q in step["questions"]),
              "lesson comes with 3 unseen non-diagnostic questions")
        check(len(res["new_confirmed_misconceptions"]) == len(diag) - 3, "high-confidence wrong picks confirmed")

        state = run.state()
        print("gaps:", state["gaps"], "| due:", state["due"])
        check(state["gaps"] == [x for x in state["roadmap"] if x not in right], "gaps = unplaced concepts, roadmap order")
        check(set(state["due"]) == right, "placed concepts have a verification review scheduled")

        lesson_cid = step["step"]["concept_id"]
        res = run.answer(step["questions"], {lesson_cid})
        print(f"{lesson_cid} mastery={res['mastery'][lesson_cid]:.3f}")
        check(res["mastery"][lesson_cid] >= 0.85, f"{lesson_cid} mastered")

        placed = diag[0]["concept_id"]
        before = run.state()
        print(f"before advance: R[{placed}]={before['retrievability'][placed]:.4f} pace={before['pace']}")
        adv = run.advance(3)
        check(right | {lesson_cid} <= set(adv["due_now"]), "placed and learned concepts due after 3 days")
        after = run.state()
        print(f"after advance: R[{placed}]={after['retrievability'][placed]:.4f} next_due={after['next_due']}")
        check(after["retrievability"][placed] < before["retrievability"][placed], "retrievability dropped")

        # --- all right ---
        run = Run(c, cid, key, "all-right")
        res = run.answer(run.start(), all_ids)
        state = run.state()
        print("gaps:", state["gaps"])
        check(state["gaps"] == [], "no gaps")
        check(res["next"]["step"]["kind"] == "done", "next step is done")
        check(f"Placed {len(all_ids)} concepts as already known; I'll check them again tomorrow." in res["messages"],
              "placement message")
        check(sum("placed as known" in m for m in res["messages"]) == 0, "placement not repeated in messages")
        adv = run.advance(1)
        check(set(adv["due_now"]) == all_ids, "every concept due for review after 1 day")

        # --- all wrong ---
        run = Run(c, cid, key, "all-wrong")
        res = run.answer(run.start(), set())
        state = run.state()
        print("gaps:", state["gaps"])
        check(state["gaps"] == state["roadmap"] and set(state["gaps"]) == all_ids, "every concept is a gap")
        nxt = res["next"]["step"]
        check(nxt["kind"] == "lesson" and nxt["concept_id"] in roots, f"next step is a lesson on a root concept {sorted(roots)}")
        check(not any(m.startswith("Placed") for m in res["messages"]), "nothing placed")
        print("\nSMOKE OK")


if __name__ == "__main__":
    main()
