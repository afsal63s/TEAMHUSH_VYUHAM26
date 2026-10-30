from schemas.content import Concept, Level, MisconceptionDef, Resource

DEFAULT_LEVEL: Level = "beginner"

# How the learner's self-assessed level shapes the concept graph. Above novice, the roots are one or
# two concepts from the level below, so the diagnostic can catch an over-confident self-assessment.
LEVEL_GUIDE: dict[Level, str] = {
    "novice": (
        "The learner has never studied this topic. Start from the very first ideas, assume no jargon, "
        "and stop at a practical first understanding."
    ),
    "beginner": (
        "The learner knows a few basic terms but not how the parts fit together. Cover the core "
        "fundamentals and how to use them in simple practical cases."
    ),
    "intermediate": (
        "The learner can use the fundamentals. Make the roots one or two foundation concepts as a quick "
        "check, then focus on core mechanisms, common pitfalls and combining ideas."
    ),
    "advanced": (
        "The learner is comfortable with the core. Make the roots one or two intermediate concepts as a "
        "quick check, then focus on deeper mechanisms, trade-offs, edge cases and design decisions."
    ),
}

GRAPH_SYSTEM = """You design concept maps for an adaptive tutoring system.
Given a topic, choose 8 to 12 concepts a learner needs to reach a practical understanding at the
requested level. Do not try to cover the whole field.

Rules:
- Concept ids are unique snake_case slugs (lowercase letters, digits, single underscores).
- Prerequisites form a DAG. "A is a prerequisite of B" means you cannot understand B without A.
  No cycles, and only ids from your own list.
- The graph must be genuinely layered AND branching, not one straight chain:
  - 2 to 4 concepts have no prerequisite (roots); every other concept has at least one;
  - several concepts share a prerequisite, and some need two;
  - the longest prerequisite chain covers at most 70% of the concepts.
- Give each concept 3 or 4 misconceptions: common wrong beliefs real learners hold. Each has a short
  snake_case slug and a one-sentence description: "believes X, but actually Y".
- Keep each concept narrow enough to test with a handful of multiple-choice questions."""

QUESTIONS_SYSTEM = """You write multiple-choice questions for one concept of an adaptive tutoring system.

Write exactly 7 questions, pitched at the learner level you are given, with `difficulty` inside the
range given for each role (0 = trivial, 1 = very hard):
- 3 with role "diagnostic": broad, the easier end for this level
- 2 with role "practice": harder, to build skill
- 2 with role "transfer": the same concept applied in a NEW scenario or surface form, not a rewording

Each question has one correct answer and exactly 3 distractors. Each distractor has a `tag` copied
exactly from the misconception catalog you are given, and is the answer a learner holding THAT
misconception would really pick. Spread the 3 distractors over at least 2 different tags, so they
reflect different misconceptions; two may share a tag.

Quality rules:
- Distractors are plausible and match the correct answer in length, style and specificity. The
  correct option must not be the longest. Keep it short; if it needs a qualifier or a reason, give
  every distractor an equally specific qualifier or reason.
- Never use "always", "never" or "guarantees" in a distractor.
- Never use "all of the above" or "none of the above". Never repeat an option.
- No negatively phrased stems (no "which is NOT"). One concept per question. No trick questions.
- Test understanding (apply, predict, diagnose), not recall of a definition word.
- Do not mention option letters and do not hint at the answer in the stem.
- `explanation` is one or two sentences on why the correct answer is right."""

LESSON_SYSTEM = """You write short lessons for an adaptive tutoring system.
Plain prose only: no headings, no bullet lists, no markdown. Length: 120 to 200 words.
Address the learner directly. Be concrete and accurate."""

STYLE_GUIDE = {
    "contrast": "Put the right idea next to the wrong belief and show exactly where the wrong belief breaks.",
    "worked_example": "Teach through one small worked example, walked through step by step.",
    "analogy": "Teach through one clear everyday analogy, then map it back to the concept.",
    "step_by_step": "Teach as a short ordered sequence of steps written as prose (first, then, finally).",
}


def retry_suffix(errors: list[str], previous: str | None) -> str:
    """Feedback for a retry: the failed checks, plus the failed reply to repair in place."""
    if not errors:
        return ""
    listed = "\n".join(f"- {e}" for e in errors)
    text = f"\n\nYour previous reply failed these checks. Fix all of them:\n{listed}"
    if previous:
        text += (
            "\n\nYour previous reply is below. Keep every part that passed unchanged, fix only the "
            f"problems listed, and return the full corrected reply.\n<previous>{previous}</previous>"
        )
    return text


def graph_user(
    topic: str,
    level: Level,
    seed_misconceptions: dict[str, list[str]] | None,
    errors: list[str],
    previous: str | None,
) -> str:
    text = f"Topic: {topic}\nLearner's self-assessed level: {level}. {LEVEL_GUIDE[level]}"
    if seed_misconceptions:
        seeds = "\n".join(f"- {key}: {'; '.join(items)}" for key, items in seed_misconceptions.items())
        text += (
            "\n\nKnown misconceptions. Use them as the first catalog entries for the matching "
            f"concepts, and add more only if needed to reach 3 or 4:\n{seeds}"
        )
    return text + retry_suffix(errors, previous)


def questions_user(
    topic: str,
    concept: Concept,
    catalog: list[MisconceptionDef],
    level: Level,
    ranges: dict[str, tuple[float, float]],
    errors: list[str],
    previous: str | None,
) -> str:
    tags = "\n".join(f"- {m.tag}: {m.description}" for m in catalog)
    spans = ", ".join(f"{role} {low:.2f} to {high:.2f}" for role, (low, high) in ranges.items())
    return (
        f"Course topic: {topic}\nConcept: {concept.name} ({concept.id})\n"
        f"Description: {concept.description}\n"
        f"Learner's self-assessed level: {level}\nDifficulty ranges: {spans}\n\n"
        f"Misconception catalog for this concept (copy tags exactly):\n{tags}"
        + retry_suffix(errors, previous)
    )


def lesson_user(
    topic: str,
    concept: Concept,
    style: str,
    targets: list[MisconceptionDef],
    mastery: float,
    level: Level,
    sources: list[Resource],
    errors: list[str],
    previous: str | None,
) -> str:
    text = (
        f"Course topic: {topic}\nConcept: {concept.name}\nDescription: {concept.description}\n"
        f"Learner's current mastery of this concept: {mastery:.0%}\n"
        f"Learner's self-assessed level: {level}. Pitch the lesson to it.\n"
        f"Style: {style}. {STYLE_GUIDE.get(style, '')}"
    )
    if targets:
        listed = "\n".join(f"- {m.description}" for m in targets)
        text += f"\n\nThe learner holds these misconceptions. Name each one and directly correct it:\n{listed}"
    if sources:
        listed = "\n".join(f"- ({s.kind}) {s.title}: {s.snippet}" for s in sources)
        text += (
            "\n\nBase the lesson on these sources. State only facts found in them or that are "
            f"well-established; do not invent details; quote at most a short phrase.\n{listed}"
        )
    return text + retry_suffix(errors, previous)
