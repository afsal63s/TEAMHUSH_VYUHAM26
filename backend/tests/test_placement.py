"""Diagnostic placement on a real fixture bundle. Concept ids come from the fixture's graph."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from api.grading import grade, topo_order
from api.learners import is_diagnostic_round, place_known, placement_message
from core import engine
from core.clock import Clock
from generation import CourseBundle
from schemas.learner import AnswerIn, BktParams, ConceptState, LearnerState, PolicyConfig

FIXTURES = sorted((Path(__file__).resolve().parent.parent / "fixtures").glob("*.json"))
THR = BktParams().mastery_threshold
NOW = datetime(2026, 1, 1, 12)


@pytest.fixture(params=FIXTURES, ids=[p.stem for p in FIXTURES])
def bundle(request) -> CourseBundle:
    return CourseBundle.model_validate(json.loads(request.param.read_text(encoding="utf-8")))


def test_fixtures_exist():
    assert FIXTURES, "no fixtures/*.json"


def diagnostic_round(bundle: CourseBundle, right: set[str]):
    """Fresh state, one diagnostic answer per concept: correct for `right`, wrong otherwise."""
    roadmap = topo_order(bundle.graph)
    state = LearnerState(learner_id="l", course_id=bundle.course_id, roadmap=roadmap,
                         concepts={c: ConceptState(concept_id=c) for c in roadmap})
    qs = {}
    for cid in roadmap:
        q = next(q for q in bundle.questions if q.concept_id == cid and q.kind == "diagnostic")
        qs[q.id] = q
    answers = [AnswerIn(question_id=q.id, chosen_index=q.correct_index if q.concept_id in right
                        else (q.correct_index + 1) % 4) for q in qs.values()]
    graded = grade(qs, answers)
    assert is_diagnostic_round(state)
    engine.submit_answers(state, list(qs.values()), graded, PolicyConfig(), Clock(NOW))
    assert not is_diagnostic_round(state)
    return state, graded, roadmap


def test_placement_marks_right_concepts_known_and_due_tomorrow(bundle):
    roadmap = topo_order(bundle.graph)
    right = set(roadmap[:3])
    state, graded, _ = diagnostic_round(bundle, right)
    wrong_before = {c: state.concepts[c].p_mastery for c in roadmap[3:]}

    placed = place_known(state, graded, NOW)

    assert set(placed) == right
    for c in right:
        cs = state.concepts[c]
        assert cs.p_mastery == THR
        assert cs.stability_days == 1.0 and cs.last_reviewed_at == NOW
        assert cs.due_at == NOW + timedelta(days=1)
    for c, p in wrong_before.items():
        assert state.concepts[c].p_mastery == p < THR and state.concepts[c].due_at is None
    assert placement_message(state, placed) == "Placed 3 concepts as already known; I'll check them again tomorrow."


def test_placed_concepts_are_skipped_then_reviewed(bundle):
    roadmap = topo_order(bundle.graph)
    state, graded, _ = diagnostic_round(bundle, set(roadmap))
    place_known(state, graded, NOW)
    assert engine.get_next(state, bundle.graph, PolicyConfig(), Clock(NOW)).kind == "done"
    step = engine.get_next(state, bundle.graph, PolicyConfig(), Clock(NOW + timedelta(days=1)))
    assert step.kind == "review" and step.concept_id in roadmap


def test_all_wrong_places_nothing(bundle):
    state, graded, roadmap = diagnostic_round(bundle, set())
    assert place_known(state, graded, NOW) == []
    step = engine.get_next(state, bundle.graph, PolicyConfig(), Clock(NOW))
    roots = {c.id for c in bundle.graph.concepts if not c.prerequisites}
    assert step.kind == "lesson" and step.concept_id in roots
