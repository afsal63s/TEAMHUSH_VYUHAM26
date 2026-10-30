"""Seeded random trajectories through core.engine on a real fixture; checks invariants after every step.

Each run: up to ROUNDS rounds of 1-4 random questions with random correctness, confidence and (for
wrong answers) a random misconception tag from the question's distractors; the clock sometimes
jumps 0-10 days. get_next runs after every round. A failure names the invariant, seed and round;
the test reports the smallest failing seed per invariant.
"""

import json
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from core import engine
from core.clock import Clock
from generation import CourseBundle
from schemas.learner import AnswerGraded, ConceptState, LearnerState, PolicyConfig

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "python_novice.json"
RUNS = 2000
ROUNDS = 60
LOOP_LIMIT = 50
DETERMINISM_SEEDS = 100
CONFIDENCE = [None, "low", "medium", "high"]
STATUSES = {"suspected", "confirmed", "resolved"}
START = datetime(2026, 1, 1, 9)

BUNDLE = CourseBundle.model_validate(json.loads(FIXTURE.read_text(encoding="utf-8")))
GRAPH = BUNDLE.graph
CONCEPT_IDS = {c.id for c in GRAPH.concepts}
BY_CONCEPT = defaultdict(list)
for _q in BUNDLE.questions:
    BY_CONCEPT[_q.concept_id].append(_q)


class Violation(Exception):
    def __init__(self, name: str, seed: int, rnd: int, detail: str):
        super().__init__(f"{name}: seed={seed} round={rnd}: {detail}")
        self.name, self.seed = name, seed


def check_state(state: LearnerState, cap: int, ever_over_cap: set[str], fail) -> None:
    for cid, cs in state.concepts.items():
        if not 0.0 <= cs.p_mastery <= 1.0:
            fail("p_mastery_range", f"{cid} p_mastery={cs.p_mastery}")
        if cs.due_at is not None:
            if cs.stability_days < 1.0:
                fail("stability_min", f"{cid} stability_days={cs.stability_days} with due_at set")
            if cs.last_reviewed_at is None or cs.due_at < cs.last_reviewed_at:
                fail("due_after_review", f"{cid} due_at={cs.due_at} last_reviewed_at={cs.last_reviewed_at}")
        if cs.needs_help and cid not in ever_over_cap:
            fail("needs_help_cause", f"{cid} needs_help but failed_rounds never exceeded {cap}")
    for tag, m in state.misconceptions.items():
        if m.evidence < 0:
            fail("evidence_nonneg", f"{tag} evidence={m.evidence}")
        if m.status not in STATUSES:
            fail("status_allowed", f"{tag} status={m.status}")


def run_one(seed: int, config: PolicyConfig = PolicyConfig()) -> LearnerState:
    rng = random.Random(seed)
    clock = Clock(START)
    state = LearnerState(learner_id=f"fuzz{seed}", course_id=BUNDLE.course_id,
                         roadmap=[c.id for c in GRAPH.concepts],
                         concepts={c.id: ConceptState(concept_id=c.id) for c in GRAPH.concepts})
    ever_over_cap: set[str] = set()
    step = None
    steps_since_end = 0
    rnd = 0

    def fail(name: str, detail: str) -> None:
        raise Violation(name, seed, rnd, detail)

    for rnd in range(1, ROUNDS + 1):
        # Pick questions: mostly from the step's concept, otherwise from anywhere.
        n = rng.randint(1, 4)
        if step is not None and step.concept_id in BY_CONCEPT and rng.random() < 0.7:
            pool = BY_CONCEPT[step.concept_id]
        else:
            pool = BUNDLE.questions
        questions = [rng.choice(pool) for _ in range(n)]
        graded = []
        for q in questions:
            correct = rng.random() < 0.5
            tags = [o.misconception_tag for o in q.options if o.misconception_tag]
            graded.append(AnswerGraded(question_id=q.id, concept_id=q.concept_id, correct=correct,
                                       chosen_tag=None if correct else rng.choice(tags),
                                       confidence=rng.choice(CONFIDENCE)))

        before = state.session_questions
        try:
            engine.submit_answers(state, questions, graded, config, clock)
        except Exception as exc:  # noqa: BLE001
            fail("no_exception", f"submit_answers raised {exc!r}")
        if state.session_questions < before:
            fail("session_monotonic", f"session_questions {before} -> {state.session_questions}")
        ever_over_cap |= {c for c, cs in state.concepts.items() if cs.failed_rounds > config.max_rounds_per_concept}
        check_state(state, config.max_rounds_per_concept, ever_over_cap, fail)

        try:
            step = engine.get_next(state, GRAPH, config, clock)
        except Exception as exc:  # noqa: BLE001
            fail("no_exception", f"get_next raised {exc!r}")
        check_state(state, config.max_rounds_per_concept, ever_over_cap, fail)
        if step.kind in ("lesson", "fallback", "review") and step.concept_id not in CONCEPT_IDS:
            fail("step_concept_exists", f"{step.kind} names concept {step.concept_id!r}")
        if step.kind == "fallback" and step.target_concept not in CONCEPT_IDS:
            fail("fallback_target_exists", f"fallback target {step.target_concept!r}")

        steps_since_end += 1
        if step.kind in ("done", "session_end"):
            steps_since_end = 0
        if steps_since_end > LOOP_LIMIT:
            fail("no_endless_loop", f"{steps_since_end} steps with a fixed clock and no done/session_end")

        if step.kind == "session_end":
            state.session_questions = 0                  # the only allowed decrease: a new session
        if rng.random() < 0.2:
            clock.advance(days=rng.uniform(0, 10))
            steps_since_end = 0                          # the loop check is for a fixed clock
    return state


def test_fuzz_invariants():
    first: dict[str, Violation] = {}
    count: dict[str, int] = defaultdict(int)
    for seed in range(RUNS):
        try:
            run_one(seed)
        except Violation as v:
            count[v.name] += 1
            if v.name not in first or v.seed < first[v.name].seed:
                first[v.name] = v
    report = "\n".join(f"{count[name]} runs; minimal: {v}" for name, v in sorted(first.items()))
    assert not first, f"invariant violations in {RUNS} runs:\n{report}"


def test_fuzz_deterministic():
    for seed in range(DETERMINISM_SEEDS):
        try:
            a = run_one(seed).model_dump()
            b = run_one(seed).model_dump()
        except Violation:
            continue                                     # reported by test_fuzz_invariants
        assert a == b, f"seed={seed}: same seed gave different final states"
