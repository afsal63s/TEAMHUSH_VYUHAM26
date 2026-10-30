"""generate_lesson prompt and result, with structured_completion stubbed (no network)."""

import asyncio
import sys
import types

if "config" not in sys.modules:
    try:
        import config  # noqa: F401
    except ModuleNotFoundError:
        # generation imports config.get_settings at import time; these tests never call it.
        sys.modules["config"] = types.ModuleType("config")
        sys.modules["config"].get_settings = lambda: None

import pytest

from generation import course_gen, prompt_hash
from generation.drafts import LessonDraft
from generation.validators import GIVEAWAY
from schemas.content import Concept, ConceptGraph, MisconceptionDef, Resource

GRAPH = ConceptGraph(
    topic="Python",
    concepts=[Concept(id="loops", name="Loops", description="Repeating code with for and while.")],
    misconceptions=[
        MisconceptionDef(tag="loops__range_inclusive", concept_id="loops", description="believes range(3) includes 3")
    ],
)
SOURCES = [
    Resource(kind="article", title="For loops explained", url="https://example.com/a", snippet="range stops before n"),
    Resource(kind="video", title="Loops in 5 minutes", url="https://example.com/v", snippet="while repeats"),
]


@pytest.fixture
def prompts_seen(monkeypatch):
    seen: list[str] = []

    async def fake(role, system, user, schema, *, max_tokens):
        seen.append(user)
        return LessonDraft(explanation=" ".join(["word"] * 150))

    monkeypatch.setattr(course_gen, "structured_completion", fake)
    return seen


def lesson(**kw):
    return asyncio.run(
        course_gen.generate_lesson(
            GRAPH, "loops", style="contrast", target_tags=["loops__range_inclusive"], mastery=0.3, **kw
        )
    )


def test_prompt_has_level_and_sources(prompts_seen):
    lesson(level="novice", sources=SOURCES)
    (user,) = prompts_seen
    assert "Learner's self-assessed level: novice. Pitch the lesson to it." in user
    assert "Base the lesson on these sources." in user
    for s in SOURCES:
        assert s.title in user


def test_resources_are_the_sources(prompts_seen):
    assert lesson(sources=SOURCES).resources == SOURCES


def test_no_sources(prompts_seen):
    result = lesson()
    assert "Base the lesson on these sources." not in prompts_seen[0]
    assert "Learner's self-assessed level: beginner." in prompts_seen[0]
    assert result.resources == []


def test_prompt_hash_stable_and_per_level():
    assert prompt_hash("Learn  Python", "novice") == prompt_hash("learn python", "novice")
    assert prompt_hash("learn python", "novice") != prompt_hash("learn python", "advanced")
    assert len(prompt_hash("learn python", "novice")) == 12


def test_giveaway_ignores_only_and_must():
    assert not GIVEAWAY.search("It must only run once")
    assert {m.group(0) for m in GIVEAWAY.finditer("always, never, guarantees")} == {"always", "never", "guarantees"}
