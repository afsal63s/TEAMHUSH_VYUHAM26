"""Research for gap concepts, run in the background and stored per (course, concept).

Research must never break or slow learning: start_research returns at once and never raises, and
get_resources returns [] until a concept's research is ready.
"""

import asyncio
import logging

from db import repos
from research.agent import research_concept
from schemas.content import Resource

logger = logging.getLogger(__name__)

CONCURRENCY = 2
_semaphore = asyncio.Semaphore(CONCURRENCY)
_tasks: set[asyncio.Task] = set()   # strong refs so running research is not garbage-collected


async def start_research(course_id: str, concept_ids: list[str],
                         targets: dict[str, list[str]] | None = None) -> None:
    """Start background research for each concept that has none yet. `targets` maps a concept to the
    descriptions of the learner's confirmed misconceptions on it. Never raises."""
    try:
        course = await repos.get_course(course_id)
        if course is None:
            return
        concepts = {c.id: c for c in course.graph.concepts}
        for concept_id in concept_ids:
            concept = concepts.get(concept_id)
            if concept is None or not await repos.mark_pending(course_id, concept_id):
                continue
            task = asyncio.create_task(_research(course_id, course.topic, course.level, concept,
                                                 (targets or {}).get(concept_id, [])))
            _tasks.add(task)
            task.add_done_callback(_tasks.discard)
    except Exception:
        logger.exception("could not start research for course %s", course_id)


async def _research(course_id: str, topic: str, level, concept, targets: list[str]) -> None:
    async with _semaphore:
        try:
            found = await research_concept(topic, concept, level, targets)
        except Exception as exc:     # research_concept only raises for the spend limit
            logger.warning("research for %s/%s failed: %s", course_id, concept.id, type(exc).__name__)
            found = []
        status = "ready" if found else "failed"
        try:
            await repos.save_resources(course_id, concept.id, status, found)
        except Exception:
            logger.exception("could not save research for %s/%s", course_id, concept.id)
            return
        logger.info("research for %s/%s: %s, %d resources", course_id, concept.id, status, len(found))


async def get_resources_doc_safe(course_id: str, concept_id: str) -> dict | None:
    try:
        return await repos.get_resources_doc(course_id, concept_id)
    except Exception:
        logger.exception("could not read research for %s/%s", course_id, concept_id)
        return None


async def get_resources(course_id: str, concept_id: str) -> list[Resource]:
    """The concept's researched resources once ready, else []. Never waits for research."""
    doc = await get_resources_doc_safe(course_id, concept_id)
    return list(doc["resources"]) if doc and doc["status"] == "ready" else []
