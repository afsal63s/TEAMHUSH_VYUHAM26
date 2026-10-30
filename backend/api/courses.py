import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from api.auth import require_master
from api.bundles import cache_bundle, find_bundle
from db import repos
from generation import CourseBundle, generate_course, prompt_hash
from schemas.api import CreateCourseIn, CreateCourseOut
from schemas.content import ConceptGraph, Course

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/courses", dependencies=[Depends(require_master)])

_tasks: set[asyncio.Task] = set()   # strong refs so running generations are not garbage-collected


def utc_naive(dt: datetime | None) -> datetime | None:
    if dt is None or dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def course_out(course: Course) -> CreateCourseOut:
    return CreateCourseOut(
        course_id=course.course_id,
        status=course.status,
        topic=course.topic,
        concepts=[{"id": c.id, "name": c.name, "prerequisites": c.prerequisites} for c in course.graph.concepts],
    )


async def save_bundle(bundle: CourseBundle, created_at: datetime, deadline: datetime | None) -> Course:
    course = Course(
        course_id=bundle.course_id, prompt=bundle.prompt, level=bundle.level, topic=bundle.graph.topic,
        graph=bundle.graph, created_at=created_at, deadline=deadline, status="ready",
        question_count=len(bundle.questions),
    )
    await repos.save_questions(bundle.questions)
    await repos.save_course(course)
    return course


async def _generate(course: Course) -> None:
    try:
        bundle = await generate_course(course.prompt, level=course.level)
        # Re-home the bundle under the id the client already has.
        bundle = bundle.model_copy(update={
            "course_id": course.course_id,
            "questions": [q.model_copy(update={"course_id": course.course_id}) for q in bundle.questions],
        })
        cache_bundle(bundle)
        await save_bundle(bundle, course.created_at, course.deadline)
        logger.info("course %s generated: %d questions", course.course_id, len(bundle.questions))
    except Exception:
        logger.exception("course %s generation failed", course.course_id)
        await repos.save_course(course.model_copy(update={"status": "failed"}))


@router.post("", response_model=CreateCourseOut)
async def create_course(body: CreateCourseIn) -> CreateCourseOut:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    deadline = utc_naive(body.deadline)

    existing = await repos.find_course_by_prompt_hash(prompt_hash(body.prompt, body.level), body.level)
    if existing and existing.status != "failed":
        if deadline and deadline != existing.deadline:
            existing = existing.model_copy(update={"deadline": deadline})
            await repos.save_course(existing)
        return course_out(existing)

    bundle = find_bundle(body.prompt, body.level)
    if bundle:
        return course_out(await save_bundle(bundle, now, deadline))

    course = Course(
        course_id=uuid.uuid4().hex[:8], prompt=body.prompt, level=body.level, topic=body.prompt,
        graph=ConceptGraph(topic=body.prompt, concepts=[], misconceptions=[]),
        created_at=now, deadline=deadline, status="generating",
    )
    await repos.save_course(course)
    task = asyncio.create_task(_generate(course))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return course_out(course)


@router.get("/{cid}", response_model=CreateCourseOut)
async def get_course(cid: str) -> CreateCourseOut:
    course = await repos.get_course(cid)
    if course is None:
        raise HTTPException(404, f"course '{cid}' not found")
    return course_out(course)
