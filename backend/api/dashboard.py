"""Single-user dashboard: password check, course cards and the review queue across courses."""

from fastapi import APIRouter, Depends

from api.auth import require_master
from api.learners import PARAMS, learner_clock
from core.scheduler import get_retrievability, is_due
from db import repos
from schemas.api import AuthCheckOut, CourseSummary, DueItem

router = APIRouter(dependencies=[Depends(require_master)])

DEFAULT_LEARNER = "me"


@router.get("/auth/check", response_model=AuthCheckOut)
async def auth_check() -> AuthCheckOut:
    """200 when the X-Master-Password header is right (or no password is set); 401 otherwise."""
    return AuthCheckOut()


@router.get("/courses", response_model=list[CourseSummary])
async def list_courses(learner_id: str = DEFAULT_LEARNER) -> list[CourseSummary]:
    out = []
    for course in await repos.list_courses():
        card = CourseSummary(course_id=course.course_id, topic=course.topic, level=course.level,
                             status=course.status, created_at=course.created_at, deadline=course.deadline,
                             concept_count=len(course.graph.concepts))
        state = await repos.get_state(learner_id, course.course_id)
        if state is not None:
            now = learner_clock(state).now()
            concepts = list(state.concepts.values())
            n = len(concepts) or 1
            due = [cs.due_at for cs in concepts if cs.due_at is not None]
            card = card.model_copy(update=dict(
                started=True,
                mastered=sum(cs.p_mastery >= PARAMS.mastery_threshold for cs in concepts),
                avg_mastery=sum(cs.p_mastery for cs in concepts) / n,
                avg_retrievability=sum(get_retrievability(cs, now) for cs in concepts) / n,
                next_due_at=min(due, default=None),
                overdue_count=sum(is_due(cs, now) for cs in concepts),
                needs_help_count=sum(cs.needs_help for cs in concepts),
                last_activity_at=state.history[-1].at if state.history else None,
            ))
        out.append(card)
    return out


@router.get("/due", response_model=list[DueItem])
async def due(learner_id: str = DEFAULT_LEARNER) -> list[DueItem]:
    """Every scheduled review across started courses, soonest first; overdue_days on the learner's clock."""
    items = []
    for course in await repos.list_courses():
        state = await repos.get_state(learner_id, course.course_id)
        if state is None:
            continue
        now = learner_clock(state).now()
        names = {c.id: c.name for c in course.graph.concepts}
        for cs in state.concepts.values():
            if cs.due_at is None:
                continue
            items.append(DueItem(
                course_id=course.course_id, topic=course.topic, concept_id=cs.concept_id,
                concept_name=names.get(cs.concept_id, cs.concept_id), due_at=cs.due_at,
                overdue_days=max(0.0, (now - cs.due_at).total_seconds() / 86400),
                retrievability=get_retrievability(cs, now),
            ))
    return sorted(items, key=lambda i: i.due_at)
