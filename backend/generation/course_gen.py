import asyncio
import hashlib
import logging
import random
import uuid
from collections import Counter
from collections.abc import Awaitable, Callable
from typing import TypeVar

from pydantic import BaseModel

from config import get_settings
from generation import prompts, validators
from generation.bundle import CourseBundle
from generation.drafts import GraphDraft, LessonDraft, QuestionDraft, QuestionsDraft
from generation.llm import structured_completion
from schemas.content import Concept, ConceptGraph, Lesson, Level, MisconceptionDef, Option, Question, Resource

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

EXTRA_ATTEMPTS = 2
# Caps leave room for Haiku's adaptive thinking, which varies widely per call; only used tokens are billed.
GRAPH_MAX_TOKENS = 8000
QUESTIONS_MAX_TOKENS = 16000
LESSON_MAX_TOKENS = 4000
ROLE_LETTER = {"diagnostic": "d", "practice": "p", "transfer": "t"}
BASE_DIFFICULTY = {"diagnostic": (0.2, 0.5), "practice": (0.5, 0.8), "transfer": (0.5, 0.8)}
LEVEL_SHIFT: dict[Level, float] = {"novice": -0.1, "beginner": 0.0, "intermediate": 0.1, "advanced": 0.2}


def difficulty_ranges(level: Level) -> dict[str, tuple[float, float]]:
    """Per-role difficulty range: the Phases.md base shifted by the learner's level, kept inside (0, 1)."""
    shift = LEVEL_SHIFT[level]
    return {
        role: (round(max(0.05, low + shift), 2), round(min(0.95, high + shift), 2))
        for role, (low, high) in BASE_DIFFICULTY.items()
    }


def prompt_hash(prompt: str, level: Level) -> str:
    """Cache key for a course prompt: case and whitespace insensitive, distinct per level."""
    key = f"{' '.join(prompt.lower().split())}|{level}"
    return hashlib.sha1(key.encode()).hexdigest()[:12]


class GenerationError(RuntimeError):
    """Generated content kept failing validation."""


async def generate_validated(
    what: str,
    call: Callable[[list[str], str | None], Awaitable[T]],
    validate: Callable[[T], list[str]],
) -> T:
    """Run `call`, validate, and on failure retry up to EXTRA_ATTEMPTS times.

    `call(errors, previous)` receives the failed checks and the failed reply as JSON, so the model
    repairs that reply instead of starting over (which brings fresh failures into parts that passed).
    """
    errors: list[str] = []
    previous: str | None = None
    for attempt in range(1, EXTRA_ATTEMPTS + 2):
        result = await call(errors, previous)
        errors = validate(result)
        if not errors:
            return result
        logger.warning(
            "validation failed for %s (attempt %d): %s",
            what, attempt, errors, extra={"validation_errors": errors},
        )
        previous = result.model_dump_json()
    raise GenerationError(f"{what}: still invalid after {EXTRA_ATTEMPTS + 1} attempts: {errors}")


def build_graph(draft: GraphDraft, prompt: str) -> ConceptGraph:
    """Final graph from a validated draft. Code, not the LLM, namespaces every tag by concept id."""
    concepts = [
        Concept(id=c.id, name=c.name, description=c.description, prerequisites=c.prerequisites)
        for c in draft.concepts
    ]
    misconceptions = [
        MisconceptionDef(
            tag=f"{c.id}__{validators.normalise_slug(m.slug)}", concept_id=c.id, description=m.description
        )
        for c in draft.concepts
        for m in c.misconceptions
    ]
    return ConceptGraph(topic=draft.topic.strip() or prompt, concepts=concepts, misconceptions=misconceptions)


async def generate_concept_graph(
    prompt: str,
    *,
    level: Level = prompts.DEFAULT_LEVEL,
    seed_misconceptions: dict[str, list[str]] | None = None,
) -> ConceptGraph:
    async def call(errors: list[str], previous: str | None) -> GraphDraft:
        user = prompts.graph_user(prompt, level, seed_misconceptions, errors, previous)
        return await structured_completion(
            "strong", prompts.GRAPH_SYSTEM, user, GraphDraft, max_tokens=GRAPH_MAX_TOKENS
        )

    draft = await generate_validated("concept graph", call, validators.validate_graph_draft)
    return build_graph(draft, prompt)


def shuffle_options(question_id: str, options: list[Option], correct_index: int) -> tuple[list[Option], int]:
    """Shuffle with an RNG seeded by the question id; return the options and the new correct index."""
    order = list(range(len(options)))
    random.Random(question_id).shuffle(order)
    return [options[i] for i in order], order.index(correct_index)


def namespace_tags(concept_id: str, catalog_tags: set[str], drafts: QuestionsDraft) -> QuestionsDraft:
    """Code owns tag namespacing: map a bare slug the model copied to its "<concept_id>__<slug>" tag."""
    for q in drafts.questions:
        for d in q.distractors:
            full = f"{concept_id}__{validators.normalise_slug(d.tag)}"
            if d.tag not in catalog_tags and full in catalog_tags:
                d.tag = full
    return drafts


def build_questions(
    course_id: str, concept_id: str, drafts: list[QuestionDraft], level: Level = prompts.DEFAULT_LEVEL
) -> list[Question]:
    ranges = difficulty_ranges(level)
    counts: Counter[str] = Counter()
    questions: list[Question] = []
    for d in drafts:
        counts[d.role] += 1
        qid = f"{course_id}-{concept_id}-{ROLE_LETTER[d.role]}{counts[d.role]}"
        options = [
            Option(text=d.correct.strip()),
            *(Option(text=x.text.strip(), misconception_tag=x.tag) for x in d.distractors),
        ]
        options, correct_index = shuffle_options(qid, options, 0)
        low, high = ranges[d.role]
        questions.append(
            Question(
                id=qid,
                course_id=course_id,
                concept_id=concept_id,
                kind=d.role,
                prompt=d.prompt.strip(),
                options=options,
                correct_index=correct_index,
                explanation=d.explanation.strip(),
                difficulty=min(max(d.difficulty, low), high),
            )
        )
    return questions


async def generate_questions_for_concept(
    graph: ConceptGraph, concept: Concept, course_id: str, *, level: Level = prompts.DEFAULT_LEVEL
) -> list[Question]:
    ranges = difficulty_ranges(level)
    catalog = [m for m in graph.misconceptions if m.concept_id == concept.id]
    tags = {m.tag for m in catalog}

    async def call(errors: list[str], previous: str | None) -> QuestionsDraft:
        user = prompts.questions_user(graph.topic, concept, catalog, level, ranges, errors, previous)
        draft = await structured_completion(
            "strong", prompts.QUESTIONS_SYSTEM, user, QuestionsDraft, max_tokens=QUESTIONS_MAX_TOKENS
        )
        return namespace_tags(concept.id, tags, draft)

    draft = await generate_validated(
        f"questions for '{concept.id}'",
        call,
        lambda d: validators.validate_concept_questions(concept.id, tags, d.questions),
    )
    for tag in sorted(validators.unused_tags(tags, draft.questions)):
        logger.warning("catalog tag never used by a question: %s", tag)
    return build_questions(course_id, concept.id, draft.questions, level)


async def generate_course(
    prompt: str,
    *,
    level: Level = prompts.DEFAULT_LEVEL,
    seed_misconceptions: dict[str, list[str]] | None = None,
    concurrency: int | None = None,
) -> CourseBundle:
    course_id = uuid.uuid4().hex[:8]
    graph = await generate_concept_graph(prompt, level=level, seed_misconceptions=seed_misconceptions)
    semaphore = asyncio.Semaphore(concurrency or get_settings().GENERATION_CONCURRENCY)

    async def for_concept(concept: Concept) -> list[Question]:
        async with semaphore:
            return await generate_questions_for_concept(graph, concept, course_id, level=level)

    per_concept = await asyncio.gather(*(for_concept(c) for c in graph.concepts))
    questions = [q for batch in per_concept for q in batch]
    return CourseBundle(course_id=course_id, prompt=prompt, level=level, graph=graph, questions=questions)


async def generate_lesson(
    graph: ConceptGraph,
    concept_id: str,
    *,
    style: str,
    target_tags: list[str],
    mastery: float,
    level: Level = prompts.DEFAULT_LEVEL,
    sources: list[Resource] | None = None,
) -> Lesson:
    concept = next((c for c in graph.concepts if c.id == concept_id), None)
    if concept is None:
        raise ValueError(f"unknown concept '{concept_id}'")
    by_tag = {m.tag: m for m in graph.misconceptions if m.concept_id == concept_id}
    unknown = [t for t in target_tags if t not in by_tag]
    if unknown:
        raise ValueError(f"unknown misconception tags for '{concept_id}': {unknown}")
    targets = [by_tag[t] for t in target_tags]

    async def call(errors: list[str], previous: str | None) -> LessonDraft:
        user = prompts.lesson_user(
            graph.topic, concept, style, targets, mastery, level, sources or [], errors, previous
        )
        return await structured_completion(
            "strong", prompts.LESSON_SYSTEM, user, LessonDraft, max_tokens=LESSON_MAX_TOKENS
        )

    draft = await generate_validated(
        f"lesson for '{concept_id}'", call, lambda d: validators.validate_lesson_text(d.explanation)
    )
    return Lesson(
        concept_id=concept_id,
        style=style,
        explanation=draft.explanation.strip(),
        targets=target_tags,
        resources=list(sources or []),
    )
