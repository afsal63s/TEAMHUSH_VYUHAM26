"""GET .../next, stored decisions and served-question validation, through the real routes.

db.repos is replaced by an in-memory store and generate_lesson by a stub: no Mongo, no LLM.
Documents round-trip through model_dump/model_validate, as they would through Mongo.
"""

import asyncio
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import dashboard, learners
from api import resources as api_resources
from api.auth import require_master
from db import repos
from generation import CourseBundle
from schemas.content import Course, Lesson, Resource
from schemas.learner import LearnerState

FIXTURE = sorted((Path(__file__).resolve().parent.parent / "fixtures").glob("*.json"))[0]
BUNDLE = CourseBundle.model_validate(json.loads(FIXTURE.read_text(encoding="utf-8")))
CID, LID = BUNDLE.course_id, "t"
BASE = f"/courses/{CID}/learners/{LID}"
KEY = {q.id: q for q in BUNDLE.questions}


class Store:
    def __init__(self) -> None:
        self.course = Course(course_id=CID, prompt=BUNDLE.prompt, level=BUNDLE.level, topic=BUNDLE.graph.topic,
                             graph=BUNDLE.graph, created_at="2026-01-01T00:00:00", status="ready")
        self.other = Course(course_id="other01", prompt="Other", level="beginner", topic="Other topic",
                            graph=BUNDLE.graph, created_at="2026-02-01T00:00:00", status="ready")
        self.courses = [self.course, self.other]
        self.states: dict[str, dict] = {}
        self.attempts: list[dict] = []
        self.lessons: dict[str, dict] = {}
        self.lesson_calls = 0
        self.lesson_sources: list[list] = []
        self.lesson_failures = 0
        self.research: dict[str, dict] = {}
        self.researched: list[tuple[str, list[str]]] = []
        self.research_result = lambda concept: [Resource(kind="article", title=f"About {concept.id}",
                                                         url=f"https://example.com/{concept.id}")]

    def state(self, lid: str = LID, cid: str = CID) -> LearnerState:
        return LearnerState.model_validate(self.states[f"{lid}:{cid}"])

    def put(self, state: LearnerState) -> None:
        self.states[f"{state.learner_id}:{state.course_id}"] = state.model_dump()


@pytest.fixture
def env(monkeypatch):
    st = Store()

    async def get_course(cid):
        return next((c for c in st.courses if c.course_id == cid), None)

    async def list_courses():
        return sorted(st.courses, key=lambda c: c.created_at, reverse=True)

    async def delete_learner(lid, cid):
        st.states.pop(f"{lid}:{cid}", None)
        st.attempts = [a for a in st.attempts if (a["lid"], a["cid"]) != (lid, cid)]

    async def get_questions(cid, concept_id=None):
        return sorted((q for q in BUNDLE.questions if concept_id in (None, q.concept_id)), key=lambda q: q.id)

    async def get_questions_by_ids(cid, ids):
        return [KEY[i] for i in ids if i in KEY]

    async def get_state(lid, cid):
        key = f"{lid}:{cid}"
        return LearnerState.model_validate(st.states[key]) if key in st.states else None

    async def save_state(state):
        st.put(state)

    async def record_attempts(lid, cid, graded, chosen, at):
        st.attempts += [{"question_id": g.question_id, "lid": lid, "cid": cid} for g in graded]

    async def seen_question_ids(lid, cid):
        return {a["question_id"] for a in st.attempts if (a["lid"], a["cid"]) == (lid, cid)}

    async def get_lesson(key):
        return Lesson.model_validate(st.lessons[key]) if key in st.lessons else None

    async def save_lesson(key, lesson):
        st.lessons[key] = lesson.model_dump()

    async def fake_generate_lesson(graph, concept_id, *, style, target_tags, mastery, level, sources):
        st.lesson_calls += 1
        if st.lesson_failures > 0:
            st.lesson_failures -= 1
            raise RuntimeError("LLM unavailable")
        st.lesson_sources.append(list(sources or []))
        return Lesson(concept_id=concept_id, style=style, explanation=f"lesson {st.lesson_calls}", targets=target_tags)

    async def get_resources_doc(course_id, concept_id):
        return st.research.get(concept_id)

    async def save_resources(course_id, concept_id, status, resources):
        st.research[concept_id] = {"status": status, "resources": list(resources)}

    async def mark_pending(course_id, concept_id):
        if concept_id in st.research:
            return False
        st.research[concept_id] = {"status": "pending", "resources": []}
        return True

    async def fake_research(topic, concept, level, targets):
        st.researched.append((concept.id, list(targets)))
        return st.research_result(concept)

    monkeypatch.setattr(api_resources, "research_concept", fake_research)
    for name, fn in [("get_resources_doc", get_resources_doc), ("save_resources", save_resources),
                     ("mark_pending", mark_pending)]:
        monkeypatch.setattr(repos, name, fn)
    for name, fn in [("get_course", get_course), ("get_questions", get_questions),
                     ("get_questions_by_ids", get_questions_by_ids), ("get_state", get_state),
                     ("save_state", save_state), ("record_attempts", record_attempts),
                     ("seen_question_ids", seen_question_ids), ("get_lesson", get_lesson),
                     ("save_lesson", save_lesson), ("list_courses", list_courses),
                     ("delete_learner", delete_learner)]:
        monkeypatch.setattr(repos, name, fn)
    monkeypatch.setattr(learners, "generate_lesson", fake_generate_lesson)
    app = FastAPI()
    app.include_router(dashboard.router)
    app.include_router(learners.router)
    app.dependency_overrides[require_master] = lambda: None   # auth has its own tests; .env may set a password
    return TestClient(app), st


def answer(qid: str, correct: bool, confidence: str | None = None) -> dict:
    q = KEY[qid]
    idx = q.correct_index if correct else next(i for i, o in enumerate(q.options) if o.misconception_tag)
    return {"question_id": qid, "chosen_index": idx, "confidence": confidence}


def diagnostic(client, right: set[str] | None = None, confidence: str | None = None) -> tuple[list[dict], dict]:
    diag = client.post(f"{BASE}/start").json()["questions"]
    right = {q["concept_id"] for q in diag} if right is None else right
    res = client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], q["concept_id"] in right, confidence)
                                                            for q in diag]})
    assert res.status_code == 200, res.text
    return diag, res.json()


def test_diagnostic_still_works_and_next_before_it_is_409(env):
    client, st = env
    diag = client.post(f"{BASE}/start").json()["questions"]
    assert len(diag) == len(BUNDLE.graph.concepts)
    assert st.state().served_question_ids == [q["id"] for q in diag]
    r = client.get(f"{BASE}/next")
    assert r.status_code == 409 and "diagnostic" in r.json()["detail"]
    first3 = {q["concept_id"] for q in diag[:3]}
    res = client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], q["concept_id"] in first3) for q in diag]})
    assert res.status_code == 200
    body = res.json()
    assert any(m.startswith("Placed 3 concepts") for m in body["messages"])
    assert body["next"]["step"]["kind"] == "lesson"
    s = st.state()
    assert s.pending_step.kind == "lesson" and s.pending_built
    assert s.pending_question_ids == s.served_question_ids == [q["id"] for q in body["next"]["questions"]]


def test_next_is_idempotent(env):
    client, st = env
    _, res = diagnostic(client, right=set())
    calls = st.lesson_calls
    snapshot = json.dumps(st.states, sort_keys=True, default=str)
    first = client.get(f"{BASE}/next").json()
    second = client.get(f"{BASE}/next").json()
    assert first == second
    assert [q["id"] for q in first["questions"]] == [q["id"] for q in res["next"]["questions"]]
    strip = lambda lesson: {k: v for k, v in lesson.items() if k != "resources"}   # noqa: E731
    assert strip(first["lesson"]) == strip(res["next"]["lesson"])   # resources may arrive once research is ready
    assert st.lesson_calls == calls                       # rebuilt from the cache, no new lesson
    assert json.dumps(st.states, sort_keys=True, default=str) == snapshot   # no state change


def test_advance_then_next_gives_a_due_review(env):
    client, st = env
    diag, _ = diagnostic(client, confidence="low")         # all placed, review due in 1 day
    adv = client.post(f"{BASE}/advance", json={"days": 1}).json()
    assert adv["next_kind"] == "review" and adv["next_concept_id"] in adv["due_now"]
    s = st.state()
    assert s.served_question_ids == [] and s.pending_question_ids == [] and not s.pending_built
    nxt = client.get(f"{BASE}/next").json()
    assert nxt["step"]["kind"] == "review" and nxt["step"]["concept_id"] == adv["next_concept_id"]
    assert len(nxt["questions"]) == 2 and all(q["concept_id"] == adv["next_concept_id"] for q in nxt["questions"])
    assert st.state().served_question_ids == [q["id"] for q in nxt["questions"]]
    res = client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], True) for q in nxt["questions"]]})
    assert res.status_code == 200


def test_unserved_questions_get_422(env):
    client, st = env
    diag, res = diagnostic(client, right=set())
    served = set(st.state().served_question_ids)
    stranger = next(q.id for q in BUNDLE.questions if q.id not in served)
    r = client.post(f"{BASE}/attempts", json={"answers": [answer(stranger, True)]})
    assert r.status_code == 422 and stranger in r.json()["detail"]
    r = client.post(f"{BASE}/attempts", json={"answers": [answer(diag[0]["id"], True)]})   # already answered
    assert r.status_code == 422 and diag[0]["id"] in r.json()["detail"]
    client.post(f"{BASE}/advance", json={"days": 1})
    ok = res["next"]["questions"][0]["id"]                 # served before advance, cleared by it
    r = client.post(f"{BASE}/attempts", json={"answers": [answer(ok, True)]})
    assert r.status_code == 422


def test_learner_stored_before_decisions_gets_a_step(env):
    client, st = env
    diagnostic(client, right=set())
    s = st.state()
    s.pending_step, s.pending_question_ids, s.served_question_ids, s.pending_built = None, [], [], False
    st.put(s)                                             # as saved by the previous version
    first = client.get(f"{BASE}/next")
    assert first.status_code == 200 and first.json()["step"]["kind"] == "lesson"
    assert client.get(f"{BASE}/next").json() == first.json()
    assert st.state().served_question_ids == [q["id"] for q in first.json()["questions"]]


def test_fallback_counted_once_across_next_calls(env):
    client, st = env
    client.post(f"{BASE}/start")
    target = next(c for c in BUNDLE.graph.concepts if c.prerequisites)
    s = st.state()
    for cid, cs in s.concepts.items():
        cs.p_mastery, cs.attempts = 0.95, 1               # mastered, nothing scheduled
    t = s.concepts[target.id]
    t.p_mastery, t.failed_rounds = 0.3, 3                 # stuck on a concept with prerequisites
    st.put(s)
    adv = client.post(f"{BASE}/advance", json={"days": 1}).json()
    assert adv["next_kind"] == "fallback"
    assert st.state().concepts[target.id].fallbacks == 1
    outs = [client.get(f"{BASE}/next").json() for _ in range(3)]
    assert outs[0] == outs[1] == outs[2]
    assert outs[0]["step"]["kind"] == "fallback" and outs[0]["step"]["target_concept"] == target.id
    assert st.state().concepts[target.id].fallbacks == 1


# --- research wiring (fake research_concept: no network) ---

def test_research_starts_for_gap_concepts_only(env):
    client, st = env
    diag = client.post(f"{BASE}/start").json()["questions"]
    right = {q["concept_id"] for q in diag[:4]}
    wrong_high = diag[4]["concept_id"]
    answers = [answer(q["id"], q["concept_id"] in right, "high") for q in diag]
    client.post(f"{BASE}/attempts", json={"answers": answers})
    gaps = [q["concept_id"] for q in diag if q["concept_id"] not in right]
    assert set(st.research) == set(gaps)                  # placed (mastered) concepts are never researched
    assert not set(st.research) & right
    state = client.get(f"{BASE}/state").json()
    assert set(st.research) == set(state["gaps"])
    out = client.get(f"{BASE}/resources").json()
    assert set(out) == set(gaps)
    assert all(v["status"] in ("pending", "ready", "failed") for v in out.values())
    assert wrong_high in out


@pytest.mark.asyncio
async def test_get_resources_is_empty_while_pending_then_ready(env):
    _, st = env
    concept = BUNDLE.graph.concepts[0]
    await repos.mark_pending(CID, concept.id)
    assert await api_resources.get_resources(CID, concept.id) == []
    await api_resources._research(CID, "t", "beginner", concept, ["a misconception"])
    assert st.research[concept.id]["status"] == "ready"
    got = await api_resources.get_resources(CID, concept.id)
    assert [r.url for r in got] == [f"https://example.com/{concept.id}"]
    assert st.researched == [(concept.id, ["a misconception"])]


@pytest.mark.asyncio
async def test_failed_research_is_marked_failed_and_does_not_raise(env, monkeypatch):
    _, st = env
    concept = BUNDLE.graph.concepts[1]

    async def boom(*args, **kwargs):
        raise RuntimeError("search is down")

    monkeypatch.setattr(api_resources, "research_concept", boom)
    await api_resources.start_research(CID, [concept.id])
    await asyncio.gather(*api_resources._tasks)
    assert st.research[concept.id] == {"status": "failed", "resources": []}
    assert await api_resources.get_resources(CID, concept.id) == []
    st.research_result = lambda c: []                     # nothing found also counts as failed
    other = BUNDLE.graph.concepts[2]
    monkeypatch.setattr(api_resources, "research_concept",
                        lambda *a, **k: asyncio.sleep(0, result=[]))
    await api_resources.start_research(CID, [other.id])
    await asyncio.gather(*api_resources._tasks)
    assert st.research[other.id]["status"] == "failed"


def test_lesson_gets_sources_and_resources_when_research_is_ready(env):
    client, st = env
    diag = client.post(f"{BASE}/start").json()["questions"]
    first = diag[0]["concept_id"]
    ready = [Resource(kind="video", title="Ready", url="https://example.com/ready")]
    st.research[first] = {"status": "ready", "resources": ready}     # research finished before the lesson
    res = client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], False) for q in diag]}).json()
    assert res["next"]["step"]["concept_id"] == first
    assert st.lesson_sources[-1] == ready                 # the lesson was written from the sources
    assert res["next"]["lesson"]["resources"] == [r.model_dump() for r in ready]
    assert client.get(f"{BASE}/next").json()["lesson"]["resources"] == res["next"]["lesson"]["resources"]


def test_lesson_without_research_is_written_without_sources(env):
    client, st = env
    diag = client.post(f"{BASE}/start").json()["questions"]
    res = client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], False) for q in diag]}).json()
    assert st.research[res["next"]["step"]["concept_id"]]["status"] in ("pending", "ready", "failed")
    if st.research[res["next"]["step"]["concept_id"]]["status"] == "pending":
        assert st.lesson_sources[-1] == []
        assert res["next"]["lesson"]["resources"] == []


# --- progress history, learning rate, lesson retry ---

def test_history_gets_one_point_per_attempt_advance_and_session(env):
    client, st = env
    diag = client.post(f"{BASE}/start").json()["questions"]
    assert st.state().history == []
    client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], True, "low") for q in diag]})
    client.get(f"{BASE}/next")
    client.get(f"{BASE}/state")
    assert [p.event for p in st.state().history] == ["attempt"]      # reads add nothing
    adv = client.post(f"{BASE}/advance", json={"days": 2}).json()
    client.post(f"{BASE}/sessions/new")
    h = st.state().history
    assert [p.event for p in h] == ["attempt", "advance", "session"]
    assert h[1].at.isoformat() == adv["now"]                          # simulated now, not wall clock
    assert h[0].questions_answered == len(diag) and h[0].mastered_count == len(diag)
    assert h[1].avg_retrievability < h[0].avg_retrievability          # two days of forgetting
    assert h[0].avg_stability_days == 1.0                             # every concept placed at 1 day


def test_history_is_capped_at_500():
    from datetime import datetime, timedelta

    from api.learners import record_history
    from schemas.learner import ConceptState, LearnerState

    s = LearnerState(learner_id="l", course_id="c", concepts={"a": ConceptState(concept_id="a")})
    t0 = datetime(2026, 1, 1)
    for i in range(510):
        record_history(s, "attempt", t0 + timedelta(minutes=i))
    assert len(s.history) == 500
    assert s.history[0].at == t0 + timedelta(minutes=10) and s.history[-1].at == t0 + timedelta(minutes=509)


def test_learning_rate_zero_without_history_positive_after_correct_answers(env):
    from api.learners import learning_rate

    client, st = env
    assert learning_rate([]) == 0.0
    diag = client.post(f"{BASE}/start").json()["questions"]
    res = client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], False, "low") for q in diag]}).json()
    one = client.get(f"{BASE}/state").json()
    assert one["learning_rate"] == 0.0 and len(one["history"]) == 1
    client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], True) for q in res["next"]["questions"]]})
    two = client.get(f"{BASE}/state").json()
    h = two["history"]
    expected = (h[-1]["avg_mastery"] - h[0]["avg_mastery"]) / (h[-1]["questions_answered"] - h[0]["questions_answered"])
    assert two["learning_rate"] > 0 and abs(two["learning_rate"] - expected) < 1e-12


def test_state_validates_with_the_new_fields(env):
    from schemas.api import MasteryOut

    client, st = env
    diag = client.post(f"{BASE}/start").json()["questions"]
    client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], i < 3, "high") for i, q in enumerate(diag)]})
    body = client.get(f"{BASE}/state").json()
    out = MasteryOut.model_validate(body)
    assert out.now is not None and len(out.history) == 1
    assert set(out.stability) == {c.id for c in BUNDLE.graph.concepts}
    assert out.avg_stability_days == 3.0                              # 3 placed with high confidence
    for key in ("concepts", "misconceptions", "due", "roadmap", "gaps", "retrievability", "pace", "days_left"):
        assert key in body                                            # existing fields unchanged


def test_next_retries_a_lesson_whose_generation_failed(env):
    client, st = env
    diag = client.post(f"{BASE}/start").json()["questions"]
    st.lesson_failures = 1
    res = client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], False) for q in diag]}).json()
    assert res["next"]["step"]["kind"] == "lesson" and res["next"]["lesson"] is None
    calls = st.lesson_calls
    nxt = client.get(f"{BASE}/next").json()
    assert nxt["lesson"] is not None and st.lesson_calls == calls + 1
    assert [q["id"] for q in nxt["questions"]] == [q["id"] for q in res["next"]["questions"]]
    s = st.state()
    assert s.pending_lesson_key in st.lessons and nxt["lesson"]["style"] in s.concepts[nxt["step"]["concept_id"]].explanations_tried
    assert client.get(f"{BASE}/next").json() == nxt and st.lesson_calls == calls + 1   # stored: no more calls


# --- B4: dashboard, reset, review log, misconception timeline, skips ---

def test_history_point_has_every_concepts_mastery(env):
    client, st = env
    diag = client.post(f"{BASE}/start").json()["questions"]
    client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], True) for q in diag]})
    client.post(f"{BASE}/advance", json={"days": 1})
    for p in st.state().history:
        assert set(p.mastery) == {c.id for c in BUNDLE.graph.concepts}


def test_auth_check_ok_and_401():
    from pydantic import SecretStr

    from config import Settings, get_settings

    app = FastAPI()
    app.include_router(dashboard.router)
    app.dependency_overrides[get_settings] = lambda: Settings(MASTER_PASSWORD=SecretStr("pw"))
    c = TestClient(app)
    assert c.get("/auth/check", headers={"X-Master-Password": "pw"}).json() == {"ok": True}
    assert c.get("/auth/check", headers={"X-Master-Password": "nope"}).status_code == 401
    assert c.get("/auth/check").status_code == 401
    app.dependency_overrides[get_settings] = lambda: Settings(MASTER_PASSWORD=SecretStr(""))
    assert c.get("/auth/check").json() == {"ok": True}


def test_courses_list_started_and_unstarted(env):
    client, st = env
    diag = client.post(f"{BASE}/start").json()["questions"]
    client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], i < 3, "low") for i, q in enumerate(diag)]})
    cards = client.get("/courses", params={"learner_id": LID}).json()
    assert [c["course_id"] for c in cards] == ["other01", CID]                  # newest first
    other, mine = cards
    assert other["started"] is False and other["mastered"] == 0 and other["next_due_at"] is None
    assert other["concept_count"] == len(BUNDLE.graph.concepts) and "graph" not in other
    assert mine["started"] is True and mine["mastered"] == 3 and mine["overdue_count"] == 0
    assert mine["next_due_at"] is not None and mine["last_activity_at"] is not None
    assert 0 < mine["avg_mastery"] < 1 and abs(mine["avg_retrievability"] - 1.0) < 1e-6
    assert client.get("/courses").json()[1]["started"] is False                # default learner "me"


def test_due_sorted_with_overdue_days_after_advance(env):
    client, st = env
    diag = client.post(f"{BASE}/start").json()["questions"]
    conf = ["low", "medium", "high"]
    client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], True, conf[i % 3]) for i, q in enumerate(diag)]})
    client.post(f"{BASE}/advance", json={"days": 3})
    items = client.get("/due", params={"learner_id": LID}).json()
    assert len(items) == len(diag)
    assert [i["due_at"] for i in items] == sorted(i["due_at"] for i in items)
    by_concept = {i["concept_id"]: i for i in items}
    for i, q in enumerate(diag):
        spacing = {"low": 1, "medium": 2, "high": 3}[conf[i % 3]]
        assert abs(by_concept[q["concept_id"]]["overdue_days"] - (3 - spacing)) < 0.01
    assert items[0]["concept_name"] and items[0]["topic"] == BUNDLE.graph.topic
    assert all(0 < i["retrievability"] <= 0.9 + 1e-6 for i in items)


def test_reset_then_start_again(env):
    client, st = env
    diag = client.post(f"{BASE}/start").json()["questions"]
    client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], True) for q in diag]})
    client.post(f"{BASE}/advance", json={"days": 5})
    st.research["x"] = {"status": "ready", "resources": []}
    assert client.post(f"{BASE}/reset").json() == {"ok": True}
    assert f"{LID}:{CID}" not in st.states and not [a for a in st.attempts if a["lid"] == LID]
    assert "x" in st.research                                                   # research is kept
    again = client.post(f"{BASE}/start")
    assert again.status_code == 200
    s = st.state()
    assert s.clock_offset_days == 0 and s.history == [] and s.reviews == [] and s.pending_step is None
    assert client.post("/courses/nope/learners/me/reset").status_code == 404


def test_review_log_days_since_seen_passed_and_delayed_rate(env):
    client, st = env
    diag = client.post(f"{BASE}/start").json()["questions"]
    client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], True, "low") for q in diag]})
    r0 = client.get(f"{BASE}/state").json()["retention"]
    assert r0["reviews_total"] == 0 and r0["review_pass_rate"] is None and r0["delayed_pass_rate"] is None
    client.post(f"{BASE}/advance", json={"days": 3})                             # short gap: not delayed
    rv = client.get(f"{BASE}/next").json()
    client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], True) for q in rv["questions"]]})
    s = st.state()
    assert len(s.reviews) == 1 and s.reviews[0].passed and abs(s.reviews[0].days_since_last_seen - 3) < 0.01
    r1 = client.get(f"{BASE}/state").json()["retention"]
    assert r1["review_pass_rate"] == 1.0 and r1["delayed_reviews_total"] == 0 and r1["delayed_pass_rate"] is None
    client.post(f"{BASE}/advance", json={"days": 10})                            # long gap: delayed
    rv = client.get(f"{BASE}/next").json()
    assert rv["step"]["kind"] == "review"
    client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], False) for q in rv["questions"]]})
    last = st.state().reviews[-1]
    assert last.concept_id == rv["step"]["concept_id"] and last.passed is False and last.days_since_last_seen >= 10
    r2 = client.get(f"{BASE}/state").json()
    assert r2["retention"]["delayed_reviews_total"] == 1 and r2["retention"]["delayed_pass_rate"] == 0.0
    marks = next(c for c in r2["concepts"] if c["concept_id"] == last.concept_id)["reviews"]
    assert marks[-1]["passed"] is False and "last_reviewed_at" in r2["concepts"][0]


def test_misconception_first_seen_and_resolved_set_once():
    from datetime import datetime, timedelta

    from api.learners import stamp_misconceptions
    from schemas.learner import LearnerState, MisconceptionState

    t = datetime(2026, 1, 1)
    prev = LearnerState(learner_id="l", course_id="c")
    s = prev.model_copy(deep=True)
    s.misconceptions["a__x"] = MisconceptionState(tag="a__x", concept_id="a", status="confirmed", evidence=2)
    stamp_misconceptions(prev, s, t)
    assert s.misconceptions["a__x"].first_seen_at == t and s.misconceptions["a__x"].resolved_at is None
    prev = s.model_copy(deep=True)
    s.misconceptions["a__x"].status = "resolved"
    stamp_misconceptions(prev, s, t + timedelta(days=1))
    assert s.misconceptions["a__x"].resolved_at == t + timedelta(days=1)
    prev = s.model_copy(deep=True)
    stamp_misconceptions(prev, s, t + timedelta(days=2))                        # still resolved: unchanged
    assert s.misconceptions["a__x"].resolved_at == t + timedelta(days=1)
    assert s.misconceptions["a__x"].first_seen_at == t
    prev = s.model_copy(deep=True)
    s.misconceptions["a__x"].status = "suspected"                                # it came back
    stamp_misconceptions(prev, s, t + timedelta(days=3))
    assert s.misconceptions["a__x"].resolved_at is None


def test_misconceptions_in_state_carry_description_and_first_seen(env):
    client, st = env
    diag = client.post(f"{BASE}/start").json()["questions"]
    client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], False, "high") for q in diag]})
    ms = client.get(f"{BASE}/state").json()["misconceptions"]
    catalog = {m.tag: m.description for m in BUNDLE.graph.misconceptions}
    assert ms and all(m["description"] == catalog[m["tag"]] and m["first_seen_at"] and m["concept_id"] for m in ms)


def test_partial_submit_grades_only_the_answered_subset(env):
    client, st = env
    diag = client.post(f"{BASE}/start").json()["questions"]
    res = client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], False) for q in diag]}).json()
    qs = res["next"]["questions"]
    before = st.state()
    out = client.post(f"{BASE}/attempts", json={"answers": [answer(qs[0]["id"], True)]}).json()
    assert [g["question_id"] for g in out["graded"]] == [qs[0]["id"]]
    assert out["skipped"] == [q["id"] for q in qs[1:]]
    assert set(out["correct_indices"]) == {qs[0]["id"]}
    after = st.state()
    cid = qs[0]["concept_id"]
    assert after.concepts[cid].attempts == before.concepts[cid].attempts + 1     # one answer, not three
    assert [a["question_id"] for a in st.attempts if a["question_id"] in {q["id"] for q in qs}] == [qs[0]["id"]]


def test_all_skipped_changes_nothing(env):
    client, st = env
    diag = client.post(f"{BASE}/start").json()["questions"]
    r = client.post(f"{BASE}/attempts", json={"answers": []})
    assert r.status_code == 409                                                  # the diagnostic cannot be skipped entirely
    res = client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], False) for q in diag]}).json()
    snapshot = json.dumps(st.states, sort_keys=True, default=str)
    out = client.post(f"{BASE}/attempts", json={"answers": []})
    assert out.status_code == 200
    body = out.json()
    assert body["graded"] == [] and body["skipped"] == [q["id"] for q in res["next"]["questions"]]
    assert body["next"]["step"] == res["next"]["step"]
    assert [q["id"] for q in body["next"]["questions"]] == [q["id"] for q in res["next"]["questions"]]
    assert json.dumps(st.states, sort_keys=True, default=str) == snapshot


def test_diagnostic_skip_leaves_concept_a_gap(env):
    client, st = env
    diag = client.post(f"{BASE}/start").json()["questions"]
    out = client.post(f"{BASE}/attempts", json={"answers": [answer(q["id"], True) for q in diag[1:]]}).json()
    assert out["skipped"] == [diag[0]["id"]]
    s = st.state()
    assert s.concepts[diag[0]["concept_id"]].p_mastery == 0.2 and s.concepts[diag[0]["concept_id"]].due_at is None
    assert diag[0]["concept_id"] in client.get(f"{BASE}/state").json()["gaps"]
    assert all(s.concepts[q["concept_id"]].p_mastery == 0.85 for q in diag[1:])


def test_unknown_id_still_422_with_valid_ones(env):
    client, st = env
    diag = client.post(f"{BASE}/start").json()["questions"]
    r = client.post(f"{BASE}/attempts", json={"answers": [answer(diag[0]["id"], True),
                                                           {"question_id": "nope", "chosen_index": 0}]})
    assert r.status_code == 422 and "nope" in r.json()["detail"]
