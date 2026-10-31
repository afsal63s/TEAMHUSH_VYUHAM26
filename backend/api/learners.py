import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from api.auth import require_master
from api.grading import GradingError, grade, pick_unseen_first, to_public, topo_order
from api.messages import messages
from api.resources import get_resources, get_resources_doc_safe, start_research
from core import engine
from core.clock import Clock
from core.scheduler import get_retrievability, is_due
from db import repos
from generation import generate_lesson
from generation.styles import choose_style
from schemas.api import (AdvanceIn, AdvanceOut, AttemptResultOut, ConceptResearch, ConceptStateOut, MasteryOut,
                         MisconceptionOut, ResetOut, Retention, ReviewMark, StartOut, StepOut, SubmitAnswersIn)
from schemas.content import Course, Lesson, Question
from schemas.learner import (HISTORY_CAP, REVIEW_LOG_CAP, AnswerGraded, BktParams, ConceptState, HistoryPoint,
                             LearnerState, PolicyConfig, ReviewEvent, Step)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/courses/{cid}/learners/{lid}", dependencies=[Depends(require_master)])

CONFIG = PolicyConfig()
PARAMS = BktParams()
LESSON_QUESTIONS = 3
REVIEW_QUESTIONS = 2


# --- loading and time ---

async def ready_course(cid: str) -> Course:
    course = await repos.get_course(cid)
    if course is None:
        raise HTTPException(404, f"course '{cid}' not found")
    if course.status != "ready":
        raise HTTPException(409, f"course '{cid}' is {course.status}")
    return course


async def load(cid: str, lid: str) -> tuple[Course, LearnerState]:
    course = await ready_course(cid)
    state = await repos.get_state(lid, cid)
    if state is None:
        raise HTTPException(404, f"learner '{lid}' has not started course '{cid}'")
    return course, state


def learner_clock(state: LearnerState) -> Clock:
    real_now = datetime.now(timezone.utc).replace(tzinfo=None)
    return Clock(real_now + timedelta(days=state.clock_offset_days))


def days_left(course: Course, now: datetime) -> int | None:
    if course.deadline is None:
        return None
    return int((course.deadline - now).total_seconds() // 86400)


# --- diagnostic placement ---

def is_diagnostic_round(state: LearnerState) -> bool:
    """The first attempts call: nothing has been answered yet."""
    return all(cs.attempts == 0 for cs in state.concepts.values())


PLACEMENT_DAYS = {"low": 1.0, "medium": 2.0, "high": 3.0}   # None (not given) counts as low


def place_known(state: LearnerState, graded: list[AnswerGraded], now: datetime,
                params: BktParams = BktParams()) -> list[str]:
    """After the diagnostic, treat each concept answered correctly as already known.

    One right answer only lifts BKT to ~0.55, which would make a learner relearn what they know.
    Placed concepts get p_mastery = threshold and a verification review whose spacing follows the
    stated confidence: low 1 day, medium 2, high 3 (the lowest if a concept had several answers).
    A guesser is caught by that review: a failed review is a lapse. Concepts answered wrong stay
    as BKT left them. The diagnostic does not count against the session budget, so the session
    counter starts again at 0. Returns the placed concept ids.
    """
    results: dict[str, bool] = {}
    days: dict[str, float] = {}
    for g in graded:
        results[g.concept_id] = results.get(g.concept_id, True) and g.correct
        d = PLACEMENT_DAYS.get(g.confidence or "low", 1.0)
        days[g.concept_id] = min(days.get(g.concept_id, d), d)
    placed = []
    for cid, all_right in results.items():
        if all_right:
            cs = state.concepts.setdefault(cid, ConceptState(concept_id=cid))
            cs.p_mastery = params.mastery_threshold
            cs.stability_days = days[cid]
            cs.last_reviewed_at = now
            cs.due_at = now + timedelta(days=days[cid])
            placed.append(cid)
    state.session_questions = 0
    return placed


def placement_message(state: LearnerState, placed: list[str]) -> str:
    longest = max(state.concepts[c].stability_days for c in placed)
    when = "tomorrow" if longest <= 1 else f"within {longest:g} days"
    return f"Placed {len(placed)} concepts as already known; I'll check them again {when}."


# --- progress history ---

LEARNING_RATE_WINDOW = 10   # answers


def record_history(state: LearnerState, event: str, now: datetime) -> None:
    """Append one progress sample (simulated now) over every concept of the course; keep the last HISTORY_CAP."""
    concepts = list(state.concepts.values())
    n = len(concepts) or 1
    stable = [cs.stability_days for cs in concepts if cs.stability_days > 0]
    state.history.append(HistoryPoint(
        at=now, event=event,
        avg_mastery=sum(cs.p_mastery for cs in concepts) / n,
        avg_retrievability=sum(get_retrievability(cs, now) for cs in concepts) / n,
        mastered_count=sum(cs.p_mastery >= PARAMS.mastery_threshold for cs in concepts),
        questions_answered=sum(cs.attempts for cs in concepts),
        avg_stability_days=sum(stable) / len(stable) if stable else 0.0,
        mastery={cs.concept_id: cs.p_mastery for cs in concepts},
    ))
    del state.history[:-HISTORY_CAP]


# --- review log and misconception timeline (API-layer bookkeeping around engine.submit_answers) ---

DELAYED_DAYS = 7


def record_review(prev: LearnerState, state: LearnerState, step: Step | None, graded: list[AnswerGraded],
                  now: datetime) -> None:
    """Log the round if the served step was a review and its concept was answered."""
    if step is None or step.kind != "review" or not any(g.concept_id == step.concept_id for g in graded):
        return
    before = prev.concepts.get(step.concept_id) or ConceptState(concept_id=step.concept_id)
    after = state.concepts[step.concept_id]
    seen = before.last_reviewed_at
    state.reviews.append(ReviewEvent(
        concept_id=step.concept_id, at=now,
        days_since_last_seen=(now - seen).total_seconds() / 86400 if seen else 0.0,
        passed=after.lapses == before.lapses,
    ))
    del state.reviews[:-REVIEW_LOG_CAP]


def stamp_misconceptions(prev: LearnerState, state: LearnerState, now: datetime) -> None:
    """first_seen_at when a misconception first appears; resolved_at when it becomes resolved (cleared if it returns)."""
    for tag, m in state.misconceptions.items():
        old = prev.misconceptions.get(tag)
        if old is None and m.first_seen_at is None:
            m.first_seen_at = now
        if m.status == "resolved" and (old is None or old.status != "resolved"):
            m.resolved_at = now
        elif m.status != "resolved":
            m.resolved_at = None


def retention(reviews: list[ReviewEvent]) -> Retention:
    delayed = [r for r in reviews if r.days_since_last_seen >= DELAYED_DAYS]
    passed = sum(r.passed for r in reviews)
    return Retention(
        reviews_total=len(reviews), reviews_passed=passed,
        review_pass_rate=passed / len(reviews) if reviews else None,
        delayed_reviews_total=len(delayed),
        delayed_pass_rate=sum(r.passed for r in delayed) / len(delayed) if delayed else None,
        delayed_threshold_days=DELAYED_DAYS,
    )


def learning_rate(history: list[HistoryPoint]) -> float:
    """Mean change in avg_mastery per answered question over the last LEARNING_RATE_WINDOW answers.

    Compares the latest point with the latest earlier point at least that many answers back (or the
    oldest point). 0 with fewer than 2 points or no answers in between.
    """
    if len(history) < 2:
        return 0.0
    last = history[-1]
    floor = last.questions_answered - LEARNING_RATE_WINDOW
    base = next((p for p in reversed(history[:-1]) if p.questions_answered <= floor), history[0])
    answered = last.questions_answered - base.questions_answered
    return (last.avg_mastery - base.avg_mastery) / answered if answered > 0 else 0.0


# --- research ---

def research_gaps(state: LearnerState) -> list[str]:
    """Concepts not mastered, roadmap order: the only ones research runs for."""
    return [c for c in state.roadmap if state.concepts[c].p_mastery < PARAMS.mastery_threshold]


def research_targets(course: Course, state: LearnerState) -> dict[str, list[str]]:
    """concept_id -> descriptions of the learner's confirmed misconceptions on it."""
    desc = {m.tag: m.description for m in course.graph.misconceptions}
    out: dict[str, list[str]] = {}
    for tag, m in state.misconceptions.items():
        if m.status == "confirmed" and tag in desc:
            out.setdefault(m.concept_id, []).append(desc[tag])
    return out


# --- the next step ---

def step_reason(step: Step, state: LearnerState, now: datetime) -> str:
    cs = state.concepts.get(step.concept_id or "") or ConceptState(concept_id=step.concept_id or "")
    if step.kind == "review":
        return (f"{cs.concept_id} review due since {cs.due_at:%Y-%m-%d}; "
                f"recall now {get_retrievability(cs, now):.2f}")
    if step.kind == "fallback":
        return f"stuck on {step.target_concept}; revisiting prerequisite {cs.concept_id} (mastery {cs.p_mastery:.2f})"
    if step.kind == "lesson":
        if step.give_up_after:
            return f"last try on {cs.concept_id} after {cs.failed_rounds} failed rounds"
        if cs.p_mastery < PARAMS.mastery_threshold and (cs.lapses or cs.stability_days > 0) and cs.failed_rounds:
            return (f"relearning {cs.concept_id} first: it was mastered, slipped to {cs.p_mastery:.2f} "
                    f"(lapses {cs.lapses})")
        if step.target_misconceptions:
            facts = [f"{t} confirmed, evidence {state.misconceptions[t].evidence:g}"
                     for t in step.target_misconceptions]
            return "; ".join(facts) + f"; {cs.concept_id} needs it"
        return f"{cs.concept_id}: mastery {cs.p_mastery:.2f}, lowest among unlocked concepts"
    if step.kind == "session_end":
        return f"{state.session_questions} questions this session; start a new session to continue"
    stuck = [c for c, s in state.concepts.items() if s.needs_help]
    return "every reachable concept is mastered" + (f"; needs help: {', '.join(stuck)}" if stuck else "")


async def lesson_for(course: Course, cs: ConceptState, step: Step, avoid: list[str]) -> tuple[str, Lesson | None]:
    """Cached by concept, targets, avoided styles and level. Returns (cache key, lesson or None on failure)."""
    sources = await get_resources(course.course_id, cs.concept_id)   # [] until research is ready: never waits
    key = repos.lesson_key(course.course_id, cs.concept_id, step.target_misconceptions, avoid, course.level,
                           grounded=bool(sources))
    if lesson := await repos.get_lesson(key):
        return key, lesson
    try:
        lesson = await generate_lesson(
            course.graph, cs.concept_id,
            style=choose_style(avoid, bool(step.target_misconceptions)),
            target_tags=step.target_misconceptions, mastery=cs.p_mastery, level=course.level,
            sources=sources,
        )
    except Exception:
        logger.exception("lesson generation failed for %s/%s", course.course_id, cs.concept_id)
        return key, None
    await repos.save_lesson(key, lesson)
    return key, lesson


async def with_resources(course: Course, lesson: Lesson | None) -> Lesson | None:
    """The lesson carrying the concept's researched resources once research is ready."""
    if lesson is None:
        return None
    ready = await get_resources(course.course_id, lesson.concept_id)
    return lesson.model_copy(update={"resources": ready}) if ready else lesson


async def build_material(course: Course, state: LearnerState, now: datetime) -> StepOut:
    """Build lesson and questions for state.pending_step and record them on the state (caller saves).

    Records the lesson style in explanations_tried, the question ids as pending and served, and the
    lesson cache key, so later GET .../next calls rebuild the same StepOut without side effects.
    """
    step = state.pending_step
    out = StepOut(step=step, reason=step_reason(step, state, now))
    if step.kind in ("lesson", "fallback", "review"):
        cs = state.concepts.setdefault(step.concept_id, ConceptState(concept_id=step.concept_id))
        pool: list[Question] = await repos.get_questions(course.course_id, cs.concept_id)
        # Practice first, then transfer, then diagnostic (already seen by everyone).
        rank = {"practice": 0, "review": 0, "transfer": 1, "diagnostic": 2}
        pool.sort(key=lambda q: (rank[q.kind], q.id))
        seen = await repos.seen_question_ids(state.learner_id, course.course_id)
        if step.kind == "review":
            picked = pick_unseen_first(pool, seen, REVIEW_QUESTIONS)
        else:
            avoid = step.avoid_styles or list(cs.explanations_tried)
            state.pending_lesson_key, out.lesson = await lesson_for(course, cs, step, avoid)
            out.lesson = await with_resources(course, out.lesson)
            if out.lesson and out.lesson.style not in cs.explanations_tried:
                cs.explanations_tried.append(out.lesson.style)
            picked = pick_unseen_first(pool, seen, LESSON_QUESTIONS)
        out.questions = [to_public(q) for q in picked]
    state.pending_question_ids = [q.id for q in out.questions]
    state.served_question_ids = list(state.pending_question_ids)
    state.pending_built = True
    return out


async def rebuild_material(course: Course, state: LearnerState, now: datetime) -> StepOut:
    """The StepOut already built for pending_step: same questions, lesson from the cache. No side effects."""
    step = state.pending_step
    by_id = {q.id: q for q in await repos.get_questions_by_ids(course.course_id, state.pending_question_ids)}
    lesson = await repos.get_lesson(state.pending_lesson_key) if state.pending_lesson_key else None
    lesson = await with_resources(course, lesson)
    return StepOut(step=step, reason=step_reason(step, state, now), lesson=lesson,
                   questions=[to_public(by_id[q]) for q in state.pending_question_ids if q in by_id])


async def retry_lesson(course: Course, state: LearnerState) -> Lesson | None:
    """Generate the pending step's lesson again after a failed attempt; store it if it works (caller saves)."""
    step = state.pending_step
    cs = state.concepts.setdefault(step.concept_id, ConceptState(concept_id=step.concept_id))
    key, lesson = await lesson_for(course, cs, step, step.avoid_styles or list(cs.explanations_tried))
    if lesson is None:
        return None
    state.pending_lesson_key = key
    if lesson.style not in cs.explanations_tried:
        cs.explanations_tried.append(lesson.style)
    return await with_resources(course, lesson)


def decide(course: Course, state: LearnerState, clock: Clock) -> Step:
    """Call engine.get_next exactly once and store the decision; materials are built later."""
    state.pending_step = engine.get_next(state, course.graph, CONFIG, clock, PARAMS)
    state.pending_question_ids, state.served_question_ids = [], []
    state.pending_lesson_key, state.pending_built = None, False
    return state.pending_step


# --- routes ---

@router.post("/start", response_model=StartOut)
async def start(cid: str, lid: str) -> StartOut:
    course = await ready_course(cid)
    if await repos.get_state(lid, cid):
        raise HTTPException(409, f"learner '{lid}' already started course '{cid}'")
    roadmap = topo_order(course.graph)
    state = LearnerState(
        learner_id=lid, course_id=cid, roadmap=roadmap,
        concepts={c: ConceptState(concept_id=c) for c in roadmap},
    )
    diagnostic: dict[str, Question] = {}
    for q in await repos.get_questions(cid):         # sorted by id
        current = diagnostic.get(q.concept_id)
        if current is None or (q.kind == "diagnostic" and current.kind != "diagnostic"):
            diagnostic[q.concept_id] = q
    questions = [diagnostic[c] for c in roadmap if c in diagnostic]
    state.served_question_ids = [q.id for q in questions]
    await repos.save_state(state)
    return StartOut(questions=[to_public(q) for q in questions])


@router.post("/attempts", response_model=AttemptResultOut)
async def submit(cid: str, lid: str, body: SubmitAnswersIn) -> AttemptResultOut:
    course, state = await load(cid, lid)
    unserved = sorted({a.question_id for a in body.answers} - set(state.served_question_ids))
    if unserved:
        raise HTTPException(422, f"questions not served to this learner: {unserved}")
    answered_ids = {a.question_id for a in body.answers}
    skipped = [q for q in state.served_question_ids if q not in answered_ids]
    if not body.answers:
        return await skip_all(course, state, skipped)
    questions = {q.id: q for q in await repos.get_questions_by_ids(cid, [a.question_id for a in body.answers])}
    try:
        graded = grade(questions, body.answers)
    except GradingError as exc:
        raise HTTPException(422, str(exc)) from exc

    clock = learner_clock(state)
    prev = state.model_copy(deep=True)
    diagnostic = is_diagnostic_round(state)
    served_step = state.pending_step
    engine.submit_answers(state, list(questions.values()), graded, CONFIG, clock, PARAMS)
    record_review(prev, state, served_step, graded, clock.now())
    stamp_misconceptions(prev, state, clock.now())
    left = days_left(course, clock.now())
    # Messages before placement, so placed concepts get one summary line, not a "mastered" line each.
    msgs = messages(prev, state, graded, days_left=left, params=PARAMS)
    placed = place_known(state, graded, clock.now(), PARAMS) if diagnostic else []
    if placed:
        msgs.append(placement_message(state, placed))
    if diagnostic:
        await start_research(cid, research_gaps(state), research_targets(course, state))
    await repos.record_attempts(lid, cid, graded, {a.question_id: a.chosen_index for a in body.answers},
                                clock.now())
    record_history(state, "attempt", clock.now())
    await repos.save_state(state)

    step = decide(course, state, clock)
    await repos.save_state(state)
    nxt = await build_material(course, state, clock.now())
    await repos.save_state(state)                    # material ids, explanations_tried
    if step.kind in ("done", "session_end"):
        msgs.append(nxt.reason)
    if placed:
        nxt.reason = f"placed as known: {', '.join(placed)}; {nxt.reason}"
    answered = {g.question_id for g in graded}
    return AttemptResultOut(
        graded=graded,
        correct_indices={qid: questions[qid].correct_index for qid in answered},
        explanations={qid: questions[qid].explanation for qid in answered},
        mastery={c: s.p_mastery for c, s in state.concepts.items()},
        new_confirmed_misconceptions=[
            t for t, m in state.misconceptions.items()
            if m.status == "confirmed" and (t not in prev.misconceptions or prev.misconceptions[t].status != "confirmed")
        ],
        messages=msgs,
        next=nxt,
        skipped=skipped,
    )


async def skip_all(course: Course, state: LearnerState, skipped: list[str]) -> AttemptResultOut:
    """Nothing answered: no grading, no state change; the same step comes back."""
    if state.pending_step is None:
        raise HTTPException(409, "the diagnostic cannot be skipped entirely: answer at least one question")
    now = learner_clock(state).now()
    nxt = (await rebuild_material(course, state, now)) if state.pending_built else \
        StepOut(step=state.pending_step, reason=step_reason(state.pending_step, state, now))
    return AttemptResultOut(graded=[], correct_indices={}, explanations={},
                            mastery={c: s.p_mastery for c, s in state.concepts.items()},
                            new_confirmed_misconceptions=[], messages=[], next=nxt, skipped=skipped)


@router.get("/state", response_model=MasteryOut)
async def get_state(cid: str, lid: str) -> MasteryOut:
    course, state = await load(cid, lid)
    now = learner_clock(state).now()
    thr = PARAMS.mastery_threshold
    order = state.roadmap + [c for c in state.concepts if c not in state.roadmap]
    concepts = [state.concepts.get(c) or ConceptState(concept_id=c) for c in order]
    due = {cs.concept_id: cs.due_at for cs in concepts if cs.due_at is not None}
    mastered = sum(cs.p_mastery >= thr for cs in concepts)
    attempts = sum(cs.attempts for cs in concepts)
    stable = [cs.stability_days for cs in concepts if cs.stability_days > 0]
    desc = {m.tag: m.description for m in course.graph.misconceptions}
    marks: dict[str, list[ReviewMark]] = {}
    for r in state.reviews:
        marks.setdefault(r.concept_id, []).append(ReviewMark(at=r.at, passed=r.passed))
    return MasteryOut(
        concepts=[ConceptStateOut(**cs.model_dump(), reviews=marks.get(cs.concept_id, [])[-20:]) for cs in concepts],
        misconceptions=[MisconceptionOut(**m.model_dump(), description=desc.get(m.tag, ""))
                        for m in state.misconceptions.values()],
        next_due=min(due.values(), default=None),
        due=due,
        roadmap=state.roadmap,
        needs_help=[cs.concept_id for cs in concepts if cs.needs_help],
        days_left=days_left(course, now),
        gaps=[cs.concept_id for cs in concepts if cs.p_mastery < thr],
        retrievability={cs.concept_id: get_retrievability(cs, now) for cs in concepts},
        pace={"mastered": mastered, "total": len(concepts),
              "attempts_per_mastered": attempts / mastered if mastered else 0.0},
        now=now,
        history=state.history,
        learning_rate=learning_rate(state.history),
        avg_stability_days=sum(stable) / len(stable) if stable else 0.0,
        stability={cs.concept_id: cs.stability_days for cs in concepts},
        retention=retention(state.reviews),
    )


@router.post("/advance", response_model=AdvanceOut)
async def advance(cid: str, lid: str, body: AdvanceIn) -> AdvanceOut:
    course, state = await load(cid, lid)
    if body.days <= 0:
        raise HTTPException(422, "days must be positive")
    state.clock_offset_days += body.days
    state.session_questions = 0                      # a new day is a new session
    clock = learner_clock(state)
    step = decide(course, state, clock)              # no materials here: advance never calls the LLM
    now = clock.now()
    record_history(state, "advance", now)
    await repos.save_state(state)
    return AdvanceOut(now=now, due_now=[c for c, cs in state.concepts.items() if is_due(cs, now)],
                      next_kind=step.kind, next_concept_id=step.concept_id)


@router.post("/sessions/new")
async def new_session(cid: str, lid: str) -> dict:
    course, state = await load(cid, lid)
    state.session_questions = 0
    clock = learner_clock(state)
    step = decide(course, state, clock)              # the session cap ended the last decision
    record_history(state, "session", clock.now())
    await repos.save_state(state)
    return {"session_questions": 0, "next_kind": step.kind, "next_concept_id": step.concept_id}


@router.get("/next", response_model=StepOut)
async def next_step(cid: str, lid: str) -> StepOut:
    """Serve the stored decision. Idempotent: materials are built once, later calls rebuild them."""
    course, state = await load(cid, lid)
    if state.pending_step is None:
        if is_diagnostic_round(state):
            raise HTTPException(409, "no step decided yet: answer the diagnostic from /start first")
        decide(course, state, learner_clock(state))  # a learner stored before decisions were kept
    now = learner_clock(state).now()
    if state.pending_built:
        out = await rebuild_material(course, state, now)
        if out.step.kind in ("lesson", "fallback") and out.lesson is None:
            out.lesson = await retry_lesson(course, state)
            await repos.save_state(state)
        return out
    out = await build_material(course, state, now)
    await repos.save_state(state)
    return out


@router.get("/resources", response_model=dict[str, ConceptResearch])
async def resources(cid: str, lid: str) -> dict[str, ConceptResearch]:
    """Research status and resources for the learner's gap concepts (only those research was started for)."""
    _, state = await load(cid, lid)
    out: dict[str, ConceptResearch] = {}
    for concept_id in research_gaps(state):
        doc = await get_resources_doc_safe(cid, concept_id)
        if doc is not None:
            out[concept_id] = ConceptResearch(status=doc["status"], resources=doc["resources"])
    return out


@router.post("/reset", response_model=ResetOut)
async def reset(cid: str, lid: str) -> ResetOut:
    """Forget this learner on this course (state, history, review log, attempts, clock offset).
    The course, its lessons and its research stay; POST .../start works again."""
    if await repos.get_course(cid) is None:
        raise HTTPException(404, f"course '{cid}' not found")
    await repos.delete_learner(lid, cid)
    return ResetOut()
