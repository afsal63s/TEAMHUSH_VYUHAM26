from collections import defaultdict

from core import scheduler
from core.bkt import bkt_update
from core.clock import Clock
from core.policy import next_step, record_misconceptions
from schemas.content import ConceptGraph, Question
from schemas.learner import AnswerGraded, BktParams, ConceptState, LearnerState, PolicyConfig, Step


def submit_answers(state: LearnerState, questions: list[Question], graded: list[AnswerGraded],
                   config: PolicyConfig, clock: Clock, params: BktParams = BktParams()) -> LearnerState:
    """One call = one round. Mutates and returns state; deep-copy before forking a learner."""
    now, thr = clock.now(), params.mastery_threshold
    q_map = {q.id: q for q in questions}
    record_misconceptions(state, graded)

    by_concept: dict[str, list[AnswerGraded]] = defaultdict(list)
    for ans in graded:
        q = q_map.get(ans.question_id)
        if q:
            by_concept[q.concept_id].append(ans)

    for cid, answers in by_concept.items():
        cs = state.concepts.setdefault(cid, ConceptState(concept_id=cid))
        was_mastered = cs.p_mastery >= thr
        was_due = scheduler.is_due(cs, now)
        any_wrong = False

        for ans in answers:
            cs.p_mastery = bkt_update(cs.p_mastery, ans.correct, params, ans.confidence)
            cs.attempts += 1
            any_wrong |= not ans.correct
            if ans.correct:
                _credit_clean_answer(state, cid, q_map[ans.question_id])
        state.session_questions += len(answers)

        # Scheduler changes at most once per round.
        if was_mastered and any_wrong:
            scheduler.lapse(cs, now)                     # forgot something it knew
        elif was_due and not any_wrong:
            scheduler.review_success(cs, now)            # passed a due review
        elif not was_mastered and cs.p_mastery >= thr:
            scheduler.first_mastery(cs, now)             # just learned it
        # else: extra practice on a mastered, not-due concept leaves the schedule alone

        if cs.p_mastery >= thr:
            cs.failed_rounds = 0
        elif any_wrong:
            cs.failed_rounds += 1                        # per round, not per answer
            if cs.failed_rounds > config.max_rounds_per_concept:
                cs.needs_help = True                     # one last try after the cap also failed
    return state


def _credit_clean_answer(state: LearnerState, cid: str, q: Question) -> None:
    """A correct answer counts toward resolving a misconception only if the question tests it."""
    tested = {o.misconception_tag for o in getattr(q, "options", []) if o.misconception_tag}
    for tag, m in state.misconceptions.items():
        if m.concept_id == cid and m.status == "confirmed" and (not tested or tag in tested):
            m.clean_streak += 1
            if m.clean_streak >= 2:
                m.status, m.evidence = "resolved", 0.0


def get_next(state: LearnerState, graph: ConceptGraph, config: PolicyConfig, clock: Clock,
             params: BktParams = BktParams()) -> Step:
    """Calls the pure policy, then records bookkeeping the policy cannot."""
    step = next_step(state, graph, config, clock.now(), params)
    if step.kind == "fallback" and step.target_concept:
        target = state.concepts.setdefault(step.target_concept, ConceptState(concept_id=step.target_concept))
        target.fallbacks += 1
        target.failed_rounds = 0          # give the target a fresh start after the detour
    return step