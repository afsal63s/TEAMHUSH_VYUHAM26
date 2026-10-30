"""Regressions for behaviour the live E2E run (results/e2e_prompt_engineering.md) proved wrong."""

from datetime import datetime, timedelta

from api.learners import place_known
from core import engine
from core.clock import Clock
from schemas.content import Concept, ConceptGraph, MisconceptionDef, Option, Question
from schemas.learner import (AnswerGraded, BktParams, ConceptState, LearnerState, MisconceptionState,
                             PolicyConfig)

THR = BktParams().mastery_threshold
T0 = datetime(2026, 1, 1, 9)


def question(qid: str, concept: str, tag: str) -> Question:
    """Option 0 is correct; every distractor carries `tag`, so the question tests it."""
    return Question(id=qid, course_id="c", concept_id=concept, kind="practice", prompt="?",
                    options=[Option(text="right")] + [Option(text=f"w{i}", misconception_tag=tag) for i in range(3)],
                    correct_index=0, explanation="", difficulty=0.5)


def graph(*ids: str) -> ConceptGraph:
    return ConceptGraph(topic="t", concepts=[Concept(id=i, name=i, description="") for i in ids],
                        misconceptions=[MisconceptionDef(tag=f"{i}__x", concept_id=i, description="") for i in ids])


# --- 1. a tag picked wrong this round is not resolved by clean answers in the same round ---

def test_same_round_wrong_pick_blocks_resolution():
    tag = "a__x"
    state = LearnerState(learner_id="l", course_id="c", concepts={"a": ConceptState(concept_id="a")})
    state.misconceptions[tag] = MisconceptionState(tag=tag, concept_id="a", status="confirmed", evidence=2.0)
    qs = [question(f"q{i}", "a", tag) for i in range(3)]
    graded = [AnswerGraded(question_id="q0", concept_id="a", correct=True),
              AnswerGraded(question_id="q1", concept_id="a", correct=True),
              AnswerGraded(question_id="q2", concept_id="a", correct=False, chosen_tag=tag)]
    engine.submit_answers(state, qs, graded, PolicyConfig(), Clock(T0))
    m = state.misconceptions[tag]
    assert m.status == "confirmed"
    assert m.clean_streak == 0


# --- 2. relearn a lapsed concept before reviewing others ---

def test_lapsed_concept_is_relearned_before_other_reviews():
    g = graph("a", "b")
    mastered = dict(p_mastery=0.95, stability_days=1.0, last_reviewed_at=T0, due_at=T0 + timedelta(days=1))
    state = LearnerState(learner_id="l", course_id="c", roadmap=["a", "b"],
                         concepts={c: ConceptState(concept_id=c, **mastered) for c in ("a", "b")})
    clock = Clock(T0 + timedelta(days=2))                # both reviews are due
    config = PolicyConfig(max_questions_per_session=1000)
    qa = question("qa", "a", "a__x")

    # Fail a's review: a lapses.
    engine.submit_answers(state, [qa], [AnswerGraded(question_id="qa", concept_id="a", correct=False,
                                                       chosen_tag="a__x")], config, clock)
    assert state.concepts["a"].lapses == 1
    step = engine.get_next(state, g, config, clock)
    assert (step.kind, step.concept_id) == ("lesson", "a")

    # Relearn a until mastered; every step meanwhile stays on a.
    for _ in range(10):
        engine.submit_answers(state, [qa], [AnswerGraded(question_id="qa", concept_id="a", correct=True)],
                              config, clock)
        step = engine.get_next(state, g, config, clock)
        if state.concepts["a"].p_mastery >= THR:
            break
        assert (step.kind, step.concept_id) == ("lesson", "a")
    assert state.concepts["a"].p_mastery >= THR
    assert (step.kind, step.concept_id) == ("review", "b")


# --- 3. placement stability from confidence, and a fresh session after the diagnostic ---

def test_placement_stability_from_confidence_and_session_reset():
    state = LearnerState(learner_id="l", course_id="c",
                         concepts={c: ConceptState(concept_id=c) for c in ("a", "b", "c")})
    graded = [AnswerGraded(question_id=f"q{c}", concept_id=c, correct=True, confidence=conf)
              for c, conf in (("a", "low"), ("b", "medium"), ("c", "high"))]
    qs = [question(f"q{c}", c, f"{c}__x") for c in ("a", "b", "c")]
    engine.submit_answers(state, qs, graded, PolicyConfig(), Clock(T0))
    assert state.session_questions == 3

    place_known(state, graded, T0)

    for c, days in (("a", 1), ("b", 2), ("c", 3)):
        cs = state.concepts[c]
        assert cs.p_mastery == THR
        assert cs.stability_days == days
        assert cs.due_at == T0 + timedelta(days=days)
    assert state.session_questions == 0
