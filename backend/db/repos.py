"""All MongoDB access. Nothing outside this module talks to Mongo."""

import hashlib
import json
from datetime import datetime, timezone

from pymongo import ASCENDING, DESCENDING, ReplaceOne
from pymongo.errors import DuplicateKeyError

from db.connection import get_db
from generation import prompt_hash
from schemas.content import Course, Lesson, Level, Question, Resource
from schemas.learner import AnswerGraded, LearnerState


async def ensure_indexes() -> None:
    db = get_db()
    await db.courses.create_index([("prompt_hash", ASCENDING), ("level", ASCENDING)])
    await db.questions.create_index([("course_id", ASCENDING), ("concept_id", ASCENDING)])
    await db.attempts.create_index([("learner_id", ASCENDING), ("course_id", ASCENDING)])


# --- courses ---

async def save_course(course: Course) -> None:
    doc = course.model_dump()
    doc["_id"] = course.course_id
    doc["prompt_hash"] = prompt_hash(course.prompt, course.level)
    await get_db().courses.replace_one({"_id": course.course_id}, doc, upsert=True)


async def get_course(course_id: str) -> Course | None:
    doc = await get_db().courses.find_one({"_id": course_id})
    return Course.model_validate(doc) if doc else None


async def fail_generating_courses() -> int:
    """Mark every course still 'generating' as 'failed'. Call at startup: a restart killed its task."""
    result = await get_db().courses.update_many({"status": "generating"}, {"$set": {"status": "failed"}})
    return result.modified_count


async def find_course_by_prompt_hash(prompt_hash: str, level: Level) -> Course | None:
    """The newest course created from this prompt and level, whatever its status."""
    doc = await get_db().courses.find_one(
        {"prompt_hash": prompt_hash, "level": level}, sort=[("created_at", DESCENDING)]
    )
    return Course.model_validate(doc) if doc else None


# --- questions ---

async def save_questions(questions: list[Question]) -> None:
    if not questions:
        return
    ops = [ReplaceOne({"_id": q.id}, {**q.model_dump(), "_id": q.id}, upsert=True) for q in questions]
    await get_db().questions.bulk_write(ops)


async def get_questions(course_id: str, concept_id: str | None = None) -> list[Question]:
    query = {"course_id": course_id}
    if concept_id is not None:
        query["concept_id"] = concept_id
    cursor = get_db().questions.find(query).sort("_id", ASCENDING)
    return [Question.model_validate(d) async for d in cursor]


async def get_questions_by_ids(course_id: str, ids: list[str]) -> list[Question]:
    cursor = get_db().questions.find({"_id": {"$in": ids}, "course_id": course_id})
    return [Question.model_validate(d) async for d in cursor]


# --- learner states ---

def _state_id(learner_id: str, course_id: str) -> str:
    return f"{learner_id}:{course_id}"


async def get_state(learner_id: str, course_id: str) -> LearnerState | None:
    doc = await get_db().learner_states.find_one({"_id": _state_id(learner_id, course_id)})
    return LearnerState.model_validate(doc) if doc else None


async def save_state(state: LearnerState) -> None:
    sid = _state_id(state.learner_id, state.course_id)
    await get_db().learner_states.replace_one({"_id": sid}, {**state.model_dump(), "_id": sid}, upsert=True)


# --- attempts ---

async def record_attempts(learner_id: str, course_id: str, graded: list[AnswerGraded],
                          chosen: dict[str, int], at: datetime) -> None:
    """One document per graded answer. `at` is the learner's simulated now."""
    if not graded:
        return
    docs = [
        {**g.model_dump(), "learner_id": learner_id, "course_id": course_id,
         "chosen_index": chosen[g.question_id], "at": at}
        for g in graded
    ]
    await get_db().attempts.insert_many(docs)


async def seen_question_ids(learner_id: str, course_id: str) -> set[str]:
    ids = await get_db().attempts.distinct("question_id", {"learner_id": learner_id, "course_id": course_id})
    return set(ids)


# --- lesson cache ---

def lesson_key(course_id: str, concept_id: str, target_tags: list[str], avoid_styles: list[str],
               level: Level, grounded: bool = False) -> str:
    # course_id is part of the key so two courses with a same-named concept never share a lesson.
    # A lesson written with research sources is cached apart from one written without them.
    parts = [course_id, concept_id, sorted(target_tags), sorted(avoid_styles), level] + (["grounded"] if grounded else [])
    raw = json.dumps(parts)
    return hashlib.sha1(raw.encode()).hexdigest()


async def get_lesson(key: str) -> Lesson | None:
    doc = await get_db().lessons.find_one({"_id": key})
    return Lesson.model_validate(doc) if doc else None


async def save_lesson(key: str, lesson: Lesson) -> None:
    await get_db().lessons.replace_one({"_id": key}, {**lesson.model_dump(), "_id": key}, upsert=True)


# --- research resources, one document per (course, concept) ---

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)   # naive UTC, like every stored datetime


def _resources_id(course_id: str, concept_id: str) -> str:
    return f"{course_id}:{concept_id}"


async def get_resources_doc(course_id: str, concept_id: str) -> dict | None:
    """{course_id, concept_id, status, resources: [Resource], updated_at}, or None if never researched."""
    doc = await get_db().resources.find_one({"_id": _resources_id(course_id, concept_id)})
    if doc is None:
        return None
    doc["resources"] = [Resource.model_validate(r) for r in doc.get("resources", [])]
    return doc


async def save_resources(course_id: str, concept_id: str, status: str, resources: list[Resource]) -> None:
    rid = _resources_id(course_id, concept_id)
    await get_db().resources.replace_one({"_id": rid}, {
        "_id": rid, "course_id": course_id, "concept_id": concept_id, "status": status,
        "resources": [r.model_dump() for r in resources], "updated_at": _utcnow(),
    }, upsert=True)


async def fail_pending_resources() -> int:
    """Mark research still 'pending' as 'failed'. Call at startup: a restart killed its task."""
    result = await get_db().resources.update_many({"status": "pending"},
                                                  {"$set": {"status": "failed", "updated_at": _utcnow()}})
    return result.modified_count


async def mark_pending(course_id: str, concept_id: str) -> bool:
    """Create a pending document. False if one already exists (research started before), so it runs once."""
    rid = _resources_id(course_id, concept_id)
    try:
        await get_db().resources.insert_one({"_id": rid, "course_id": course_id, "concept_id": concept_id,
                                             "status": "pending", "resources": [], "updated_at": _utcnow()})
    except DuplicateKeyError:
        return False
    return True
