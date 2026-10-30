"""Rule-based encouragement: fixed templates filled with facts. No LLM."""

from schemas.learner import AnswerGraded, BktParams, ConceptState, LearnerState

STREAK = 3


def _longest_run(graded: list[AnswerGraded]) -> int:
    best = run = 0
    for g in graded:
        run = run + 1 if g.correct else 0
        best = max(best, run)
    return best


def messages(prev: LearnerState, new: LearnerState, graded: list[AnswerGraded], *,
             days_left: int | None = None, params: BktParams = BktParams()) -> list[str]:
    thr = params.mastery_threshold
    out: list[str] = []

    for cid, cs in new.concepts.items():
        old = prev.concepts.get(cid) or ConceptState(concept_id=cid)
        if old.p_mastery < thr <= cs.p_mastery:
            out.append(f"You mastered {cid} (mastery {cs.p_mastery:.2f}).")
        if cs.lapses > old.lapses:
            out.append(f"You slipped on {cid}. This happens, it is why reviews exist.")
        elif old.stability_days > 0 and cs.stability_days > old.stability_days:
            out.append(f"Review of {cid} passed: next one in {cs.stability_days:.1f} days.")
        if cs.needs_help and not old.needs_help:
            out.append(f"{cid} is flagged for help: it may need a different resource or a person.")

    for tag, m in new.misconceptions.items():
        old_m = prev.misconceptions.get(tag)
        if m.status == "resolved" and old_m is not None and old_m.status != "resolved":
            out.append(f"Misconception {tag} resolved.")

    if _longest_run(graded) >= STREAK:
        out.append(f"{STREAK} correct in a row.")
    if days_left is not None and 0 <= days_left <= 3:
        out.append(f"{days_left} day{'s' if days_left != 1 else ''} left before your deadline.")
    return out
