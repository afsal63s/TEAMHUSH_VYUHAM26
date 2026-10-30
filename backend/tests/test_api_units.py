"""grade(), messages() and the master password dependency. No Mongo, no LLM, no network."""

from datetime import datetime

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from api.auth import require_master
from api.grading import GradingError, grade, pick_unseen_first, topo_order
from api.messages import messages
from config import Settings, get_settings
from schemas.content import Concept, ConceptGraph, Option, Question
from schemas.learner import AnswerGraded, AnswerIn, ConceptState, LearnerState, MisconceptionState


def q(qid: str, concept: str = "loops", correct: int = 1) -> Question:
    opts = [Option(text=f"o{i}", misconception_tag=None if i == correct else f"{concept}__tag{i}") for i in range(4)]
    return Question(id=qid, course_id="c", concept_id=concept, kind="practice", prompt="?", options=opts,
                    correct_index=correct, explanation="because", difficulty=0.5)


# --- grade ---

def test_grade_correct_has_no_tag():
    [g] = grade({"q1": q("q1")}, [AnswerIn(question_id="q1", chosen_index=1, confidence="high")])
    assert g.correct and g.chosen_tag is None and g.concept_id == "loops" and g.confidence == "high"


def test_grade_wrong_copies_chosen_tag():
    [g] = grade({"q1": q("q1")}, [AnswerIn(question_id="q1", chosen_index=3)])
    assert not g.correct and g.chosen_tag == "loops__tag3"


def test_grade_keeps_answer_order():
    qs = {"a": q("a", correct=0), "b": q("b", "lists", correct=2)}
    out = grade(qs, [AnswerIn(question_id="b", chosen_index=2), AnswerIn(question_id="a", chosen_index=1)])
    assert [(g.question_id, g.correct, g.concept_id) for g in out] == [("b", True, "lists"), ("a", False, "loops")]


@pytest.mark.parametrize("answer", [AnswerIn(question_id="nope", chosen_index=0),
                                    AnswerIn(question_id="q1", chosen_index=4),
                                    AnswerIn(question_id="q1", chosen_index=-1)])
def test_grade_rejects_unknown_question_or_option(answer):
    with pytest.raises(GradingError):
        grade({"q1": q("q1")}, [answer])


# --- small helpers ---

def test_topo_order_prerequisites_first_ties_in_graph_order():
    graph = ConceptGraph(topic="t", misconceptions=[], concepts=[
        Concept(id="functions", name="f", description="", prerequisites=["loops", "lists"]),
        Concept(id="loops", name="l", description="", prerequisites=["variables"]),
        Concept(id="lists", name="li", description="", prerequisites=["variables"]),
        Concept(id="variables", name="v", description=""),
    ])
    assert topo_order(graph) == ["variables", "loops", "lists", "functions"]


def test_pick_unseen_first_reuses_seen_when_short():
    pool = [q("a"), q("b"), q("c")]
    assert [x.id for x in pick_unseen_first(pool, {"a", "c"}, 2)] == ["b", "a"]


# --- messages ---

def state(**concepts: ConceptState) -> LearnerState:
    return LearnerState(learner_id="l", course_id="c", concepts=dict(concepts))


def ans(correct: bool) -> AnswerGraded:
    return AnswerGraded(question_id="x", concept_id="loops", correct=correct)


def test_message_mastery_crossed():
    prev = state(loops=ConceptState(concept_id="loops", p_mastery=0.8))
    new = state(loops=ConceptState(concept_id="loops", p_mastery=0.9))
    assert messages(prev, new, [ans(True)]) == ["You mastered loops (mastery 0.90)."]


def test_message_streak_of_three_only():
    s = state()
    assert messages(s, s, [ans(True), ans(True), ans(False), ans(True)]) == []
    assert messages(s, s, [ans(False), ans(True), ans(True), ans(True)]) == ["3 correct in a row."]


def test_message_lapse_and_review_passed():
    t = datetime(2026, 1, 1)
    prev = state(a=ConceptState(concept_id="a", stability_days=2.5, last_reviewed_at=t),
                 b=ConceptState(concept_id="b", stability_days=1.0, last_reviewed_at=t))
    new = state(a=ConceptState(concept_id="a", stability_days=1.25, lapses=1, p_mastery=0.5),
                b=ConceptState(concept_id="b", stability_days=2.5))
    out = messages(prev, new, [])
    assert "You slipped on a. This happens, it is why reviews exist." in out
    assert "Review of b passed: next one in 2.5 days." in out


def test_first_mastery_is_not_a_review():
    prev = state(a=ConceptState(concept_id="a", p_mastery=0.9))
    new = state(a=ConceptState(concept_id="a", p_mastery=0.9, stability_days=1.0))
    assert messages(prev, new, []) == []


def test_message_misconception_resolved_and_needs_help():
    prev = state(a=ConceptState(concept_id="a"))
    prev.misconceptions["a__x"] = MisconceptionState(tag="a__x", concept_id="a", status="confirmed")
    new = state(a=ConceptState(concept_id="a", needs_help=True))
    new.misconceptions["a__x"] = MisconceptionState(tag="a__x", concept_id="a", status="resolved")
    out = messages(prev, new, [])
    assert "Misconception a__x resolved." in out
    assert any(m.startswith("a is flagged for help") for m in out)


@pytest.mark.parametrize("days,expected", [(5, []), (3, ["3 days left before your deadline."]),
                                           (1, ["1 day left before your deadline."]), (-1, []), (None, [])])
def test_message_deadline(days, expected):
    s = state()
    assert messages(s, s, [], days_left=days) == expected


# --- master password ---

def client(password: str) -> TestClient:
    app = FastAPI()

    @app.get("/x", dependencies=[Depends(require_master)])
    def x():
        return {"ok": True}

    app.dependency_overrides[get_settings] = lambda: Settings(MASTER_PASSWORD=SecretStr(password))
    return TestClient(app)


def test_password_missing_header_is_401():
    assert client("s3cret").get("/x").status_code == 401


def test_password_wrong_is_401():
    assert client("s3cret").get("/x", headers={"X-Master-Password": "nope"}).status_code == 401


def test_password_right_is_200():
    assert client("s3cret").get("/x", headers={"X-Master-Password": "s3cret"}).status_code == 200


def test_password_empty_means_open():
    assert client("").get("/x").status_code == 200
