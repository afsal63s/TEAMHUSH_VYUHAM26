import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from api.auth import require_master
from api.grading import GradingError, grade, pick_unseen_first, to_public, topo_order
from api.messages import messages
from api.resources import get_resources
from core import engine
from core.clock import Clock
from core.scheduler import first_mastery, get_retrievability, is_due
from db import repos
from generation import generate_lesson
from generation.styles import choose_style
from schemas.api import (AdvanceIn, AdvanceOut, AttemptResultOut, MasteryOut, StartOut, StepOut,
                         SubmitAnswersIn)
from schemas.content import Course, Lesson, Question
from schemas.learner import AnswerGraded, BktParams, ConceptState, LearnerState, PolicyConfig, Step

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


def place_known(state: LearnerState, graded: list[AnswerGraded], now: datetime,
                params: BktParams = BktParams()) -> list[str]:
    """After the diagnostic, treat each concept answered correctly as already known.

    One right answer only lifts BKT to ~0.55, which would make a learner relearn what they know.
    Placed concepts get p_mastery = threshold and a first-mastery schedule, so a verification
    review is due in 1 day. A guesser is caught by that review: a failed review is a lapse.
    Concepts answered wrong stay as BKT left them. Returns the placed concept ids.
    """
    results: dict[str, bool] = {}
    for g in graded:
        results[g.concept_id] = results.get(g.concept_id, True) and g.correct
    placed = []
    for cid, all_right in results.items():
        if all_right:
            cs = state.concepts.setdefault(cid, ConceptState(concept_id=cid))
            cs.p_mastery = params.mastery_threshold
            first_mastery(cs, now)
            placed.append(cid)
    return placed


def placement_message(placed: list[str]) -> str:
    return f"Placed {len(placed)} concepts as already known; I'll check them again tomorrow."


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
        if step.target_misconceptions:
            facts = [f"{t} confirmed, evidence {state.misconceptions[t].evidence:g}"
                     for t in step.target_misconceptions]
            return "; ".join(facts) + f"; {cs.concept_id} needs it"
        return f"{cs.concept_id}: mastery {cs.p_mastery:.2f}, lowest among unlocked concepts"
    if step.kind == "session_end":
        return f"{state.session_questions} questions this session; start a new session to continue"
    stuck = [c for c, s in state.concepts.items() if s.needs_help]
    return "every reachable concept is mastered" + (f"; needs help: {', '.join(stuck)}" if stuck else "")


async def lesson_for(course: Course, cs: ConceptState, step: Step, avoid: list[str]) -> Lesson | None:
    """Cached by concept, targets, avoided styles and level. None if generation fails."""
    key = repos.lesson_key(course.course_id, cs.concept_id, step.target_misconceptions, avoid, course.level)
    if lesson := await repos.get_lesson(key):
        return lesson
    try:
        lesson = await generate_lesson(
            course.graph, cs.concept_id,
            style=choose_style(avoid, bool(step.target_misconceptions)),
            target_tags=step.target_misconceptions, mastery=cs.p_mastery, level=course.level,
            sources=await get_resources(course.course_id, cs.concept_id),
        )
    except Exception:
        logger.exception("lesson generation failed for %s/%s", course.course_id, cs.concept_id)
        return None
    await repos.save_lesson(key, lesson)
    return lesson


async def step_out(course: Course, state: LearnerState, step: Step, now: datetime) -> StepOut:
    """Attach material to the step. Records the lesson style on the state (caller saves)."""
    out = StepOut(step=step, reason=step_reason(step, state, now))
    if step.kind not in ("lesson", "fallback", "review"):
        return out
    cs = state.concepts.setdefault(step.concept_id, ConceptState(concept_id=step.concept_id))
    pool: list[Question] = await repos.get_questions(course.course_id, cs.concept_id)
    # Practice first, then transfer, then diagnostic (already seen by everyone).
    rank = {"practice": 0, "review": 0, "transfer": 1, "diagnostic": 2}
    pool.sort(key=lambda q: (rank[q.kind], q.id))
    seen = await repos.seen_question_ids(state.learner_id, course.course_id)

    if step.kind == "review":
        out.questions = [to_public(q) for q in pick_unseen_first(pool, seen, REVIEW_QUESTIONS)]
        return out

    avoid = step.avoid_styles or list(cs.explanations_tried)
    out.lesson = await lesson_for(course, cs, step, avoid)
    if out.lesson and out.lesson.style not in cs.explanations_tried:
        cs.explanations_tried.append(out.lesson.style)
    out.questions = [to_public(q) for q in pick_unseen_first(pool, seen, LESSON_QUESTIONS)]
    return out


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
    await repos.save_state(state)

    diagnostic: dict[str, Question] = {}
    for q in await repos.get_questions(cid):         # sorted by id
        current = diagnostic.get(q.concept_id)
        if current is None or (q.kind == "diagnostic" and current.kind != "diagnostic"):
            diagnostic[q.concept_id] = q
    return StartOut(questions=[to_public(diagnostic[c]) for c in roadmap if c in diagnostic])


@router.post("/attempts", response_model=AttemptResultOut)
async def submit(cid: str, lid: str, body: SubmitAnswersIn) -> AttemptResultOut:
    course, state = await load(cid, lid)
    if not body.answers:
        raise HTTPException(422, "no answers")
    questions = {q.id: q for q in await repos.get_questions_by_ids(cid, [a.question_id for a in body.answers])}
    try:
        graded = grade(questions, body.answers)
    except GradingError as exc:
        raise HTTPException(422, str(exc)) from exc

    clock = learner_clock(state)
    prev = state.model_copy(deep=True)
    diagnostic = is_diagnostic_round(state)
    engine.submit_answers(state, list(questions.values()), graded, CONFIG, clock, PARAMS)
    left = days_left(course, clock.now())
    # Messages before placement, so placed concepts get one summary line, not a "mastered" line each.
    msgs = messages(prev, state, graded, days_left=left, params=PARAMS)
    placed = place_known(state, graded, clock.now(), PARAMS) if diagnostic else []
    if placed:
        msgs.append(placement_message(placed))
    await repos.record_attempts(lid, cid, graded, {a.question_id: a.chosen_index for a in body.answers},
                                clock.now())
    await repos.save_state(state)

    step = engine.get_next(state, course.graph, CONFIG, clock, PARAMS)
    await repos.save_state(state)
    nxt = await step_out(course, state, step, clock.now())
    await repos.save_state(state)                    # explanations_tried
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
    )


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
    return MasteryOut(
        concepts=concepts,
        misconceptions=list(state.misconceptions.values()),
        next_due=min(due.values(), default=None),
        due=due,
        roadmap=state.roadmap,
        needs_help=[cs.concept_id for cs in concepts if cs.needs_help],
        days_left=days_left(course, now),
        gaps=[cs.concept_id for cs in concepts if cs.p_mastery < thr],
        retrievability={cs.concept_id: get_retrievability(cs, now) for cs in concepts},
        pace={"mastered": mastered, "total": len(concepts),
              "attempts_per_mastered": attempts / mastered if mastered else 0.0},
    )


@router.post("/advance", response_model=AdvanceOut)
async def advance(cid: str, lid: str, body: AdvanceIn) -> AdvanceOut:
    _, state = await load(cid, lid)
    if body.days <= 0:
        raise HTTPException(422, "days must be positive")
    state.clock_offset_days += body.days
    state.session_questions = 0                      # a new day is a new session
    await repos.save_state(state)
    now = learner_clock(state).now()
    return AdvanceOut(now=now, due_now=[c for c, cs in state.concepts.items() if is_due(cs, now)])


@router.post("/sessions/new")
async def new_session(cid: str, lid: str) -> dict:
    _, state = await load(cid, lid)
    state.session_questions = 0
    await repos.save_state(state)
    return {"session_questions": 0}
