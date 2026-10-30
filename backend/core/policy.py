from datetime import datetime

from core.scheduler import get_retrievability, is_due
from schemas.content import ConceptGraph
from schemas.learner import (AnswerGraded, BktParams, ConceptState, LearnerState,
                             MisconceptionState, PolicyConfig, Step)


def _cs(state: LearnerState, cid: str) -> ConceptState:
    return state.concepts.get(cid) or ConceptState(concept_id=cid)


def record_misconceptions(state: LearnerState, graded: list[AnswerGraded]) -> None:
    """Evidence from tagged wrong picks. A resolved misconception can come back."""
    for ans in graded:
        if ans.correct or not ans.chosen_tag:
            continue
        m = state.misconceptions.setdefault(
            ans.chosen_tag, MisconceptionState(tag=ans.chosen_tag, concept_id=ans.concept_id))
        if m.status == "resolved":          # regression: start counting again
            m.status, m.evidence = "suspected", 0.0
        m.evidence += 2.0 if ans.confidence == "high" else 1.0
        m.clean_streak = 0
        if m.evidence >= 2.0:
            m.status = "confirmed"


def next_step(state: LearnerState, graph: ConceptGraph, config: PolicyConfig,
              now: datetime, params: BktParams = BktParams()) -> Step:
    thr = params.mastery_threshold

    if state.session_questions >= config.max_questions_per_session:
        return Step(kind="session_end")

    if not config.adaptive:
        # Static baseline: fixed full order, no reviews, no targeting.
        order = state.roadmap or [c.id for c in graph.concepts]
        for cid in order:
            cs = _cs(state, cid)
            if cs.p_mastery < thr and not cs.needs_help:
                return Step(kind="lesson", concept_id=cid)
        return Step(kind="done")

    # 1. Due reviews, most faded first.
    if config.spaced_review:
        due = [cs for cs in state.concepts.values() if is_due(cs, now)]
        if due:
            cs = min(due, key=lambda c: get_retrievability(c, now))
            return Step(kind="review", concept_id=cs.concept_id)

    # 2. Unlocked, unmastered concepts, lowest effective mastery first.
    candidates = []
    for c in graph.concepts:
        cs = _cs(state, c.id)
        if cs.p_mastery >= thr or cs.needs_help:
            continue
        if all(_cs(state, p).p_mastery >= thr for p in c.prerequisites):
            candidates.append((cs.p_mastery * get_retrievability(cs, now), c))
    if not candidates:
        return Step(kind="done")
    _, target = min(candidates, key=lambda x: x[0])
    cs = _cs(state, target.id)

    # 3. Stuck: fall back once to the most faded prerequisite, then give up.
    if cs.failed_rounds >= config.max_rounds_per_concept:
        if target.prerequisites and cs.fallbacks == 0:
            prereq = min(target.prerequisites,
                         key=lambda p: get_retrievability(_cs(state, p), now) * _cs(state, p).p_mastery)
            return Step(kind="fallback", concept_id=prereq, target_concept=target.id)
        return Step(kind="lesson", concept_id=target.id, give_up_after=True)

    # 4. Normal lesson.
    tags = []
    if config.target_misconceptions:
        tags = [t for t, m in state.misconceptions.items()
                if m.status == "confirmed" and m.concept_id == target.id]
    return Step(kind="lesson", concept_id=target.id,
                target_misconceptions=tags, avoid_styles=list(cs.explanations_tried))