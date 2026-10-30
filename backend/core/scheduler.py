from datetime import datetime, timedelta

from schemas.learner import ConceptState

GROWTH = 2.5          # 1 + 1.5 * score, with score = 1 for an MCQ
TARGET_RECALL = 0.9   # a review is due when retrievability falls to this


def first_mastery(state: ConceptState, now: datetime) -> None:
    state.stability_days = 1.0
    _set_due(state, now)


def review_success(state: ConceptState, now: datetime) -> None:
    state.stability_days = max(1.0, state.stability_days) * GROWTH
    _set_due(state, now)


def lapse(state: ConceptState, now: datetime) -> None:
    state.stability_days = max(1.0, state.stability_days / 2.0)
    state.p_mastery = min(state.p_mastery, 0.5)
    state.lapses += 1
    _set_due(state, now)


def _set_due(state: ConceptState, now: datetime) -> None:
    state.last_reviewed_at = now
    state.due_at = now + timedelta(days=state.stability_days)


def is_due(state: ConceptState, now: datetime) -> bool:
    return state.due_at is not None and state.due_at <= now


def get_retrievability(state: ConceptState, now: datetime) -> float:
    """0.9 ** (t / S). A concept never mastered has nothing to forget yet, so 1.0."""
    if state.last_reviewed_at is None or state.stability_days <= 0:
        return 1.0
    t = (now - state.last_reviewed_at).total_seconds() / 86400.0
    return TARGET_RECALL ** (t / state.stability_days)