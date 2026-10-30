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

from api import learners
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
        self.states: dict[str, dict] = {}
        self.attempts: list[dict] = []
        self.lessons: dict[str, dict] = {}
        self.lesson_calls = 0
        self.lesson_sources: list[list] = []
        self.research: dict[str, dict] = {}
        self.researched: list[tuple[str, list[str]]] = []
        self.research_result = lambda concept: [Resource(kind="article", title=f"About {concept.id}",
                                                         url=f"https://example.com/{concept.id}")]

    def state(self) -> LearnerState:
        return LearnerState.model_validate(self.states[LID])

    def put(self, state: LearnerState) -> None:
        self.states[LID] = state.model_dump()


@pytest.fixture
def env(monkeypatch):
    st = Store()

    async def get_course(cid):
        return st.course if cid == CID else None

    async def get_questions(cid, concept_id=None):
        return sorted((q for q in BUNDLE.questions if concept_id in (None, q.concept_id)), key=lambda q: q.id)

    async def get_questions_by_ids(cid, ids):
        return [KEY[i] for i in ids if i in KEY]

    async def get_state(lid, cid):
        return LearnerState.model_validate(st.states[lid]) if lid in st.states else None

    async def save_state(state):
        st.states[state.learner_id] = state.model_dump()

    async def record_attempts(lid, cid, graded, chosen, at):
        st.attempts += [{"question_id": g.question_id} for g in graded]

    async def seen_question_ids(lid, cid):
        return {a["question_id"] for a in st.attempts}

    async def get_lesson(key):
        return Lesson.model_validate(st.lessons[key]) if key in st.lessons else None

    async def save_lesson(key, lesson):
        st.lessons[key] = lesson.model_dump()

    async def fake_generate_lesson(graph, concept_id, *, style, target_tags, mastery, level, sources):
        st.lesson_calls += 1
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
                     ("save_lesson", save_lesson)]:
        monkeypatch.setattr(repos, name, fn)
    monkeypatch.setattr(learners, "generate_lesson", fake_generate_lesson)
    app = FastAPI()
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
