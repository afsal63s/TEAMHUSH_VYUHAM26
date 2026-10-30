"""Checks beyond the Pydantic validators.

Every validator returns a list of "<check>: detail" strings; an empty list means valid. The text
is fed back to the model on retry, so each message says exactly what to change.
"""

import math
import re

from generation.drafts import GraphDraft, QuestionDraft

SLUG = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
BANNED_OPTION = re.compile(r"\b(all|none) of the above\b", re.IGNORECASE)
GIVEAWAY = re.compile(r"\b(always|never|guarantees)\b", re.IGNORECASE)
QUESTIONS_PER_ROLE = {"diagnostic": 3, "practice": 2, "transfer": 2}
MIN_CONCEPTS, MAX_CONCEPTS = 8, 12
MIN_ROOTS, MAX_ROOTS = 2, 4
MAX_CHAIN_SHARE = 0.7
MIN_MISCONCEPTIONS = 3
LONGEST_FACTOR = 1.4
LONGEST_MIN_GAP = 10  # chars; short answers such as code output are not judged by ratio
LESSON_WORDS = (120, 200)


def normalise_slug(slug: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", slug.lower()).strip("_")


def validate_graph_draft(draft: GraphDraft) -> list[str]:
    errors: list[str] = []
    concepts = draft.concepts
    ids = [c.id for c in concepts]
    known = set(ids)
    if not MIN_CONCEPTS <= len(concepts) <= MAX_CONCEPTS:
        errors.append(f"concept_count: need {MIN_CONCEPTS} to {MAX_CONCEPTS} concepts, got {len(concepts)}")
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        errors.append(f"duplicate_id: concept id '{dup}' appears more than once")
    for cid in ids:
        if not SLUG.match(cid):
            errors.append(f"bad_id: '{cid}' is not a snake_case slug")
    for c in concepts:
        for p in c.prerequisites:
            if p == c.id:
                errors.append(f"self_prerequisite: '{c.id}' requires itself")
            elif p not in known:
                errors.append(f"unknown_prerequisite: '{c.id}' requires unknown '{p}'")
    cyclic = _has_cycle(draft)
    if cyclic:
        errors.append("cycle: prerequisites contain a cycle")
    roots = [c.id for c in concepts if not c.prerequisites]
    if concepts and not MIN_ROOTS <= len(roots) <= MAX_ROOTS:
        errors.append(f"root_count: need {MIN_ROOTS} to {MAX_ROOTS} concepts without prerequisites, got {len(roots)}")
    if concepts and (len(concepts) - len(roots)) * 2 < len(concepts):
        errors.append("flat_graph: at least 50% of concepts need a prerequisite")
    if concepts and not cyclic:
        chain, limit = longest_chain(draft), int(MAX_CHAIN_SHARE * len(concepts))
        if chain > limit:
            errors.append(
                f"long_chain: longest prerequisite chain has {chain} concepts, max {limit}; "
                "make the graph branch instead of one straight line"
            )
    for c in concepts:
        slugs = [normalise_slug(m.slug) for m in c.misconceptions]
        if len(slugs) < MIN_MISCONCEPTIONS:
            errors.append(f"few_misconceptions: '{c.id}' has {len(slugs)}, need at least {MIN_MISCONCEPTIONS}")
        if len(set(slugs)) < len(slugs):
            errors.append(f"duplicate_tag: '{c.id}' has duplicate misconception slugs")
    return errors


def _edges(draft: GraphDraft) -> dict[str, list[str]]:
    known = {c.id for c in draft.concepts}
    return {c.id: [p for p in c.prerequisites if p in known and p != c.id] for c in draft.concepts}


def _has_cycle(draft: GraphDraft) -> bool:
    edges = _edges(draft)
    state: dict[str, int] = {}  # 1 = on the current path, 2 = finished

    def visit(node: str) -> bool:
        state[node] = 1
        for nxt in edges[node]:
            if state.get(nxt) == 1 or (nxt not in state and visit(nxt)):
                return True
        state[node] = 2
        return False

    return any(n not in state and visit(n) for n in edges)


def longest_chain(draft: GraphDraft) -> int:
    """Number of concepts on the longest prerequisite path. The graph must be acyclic."""
    edges = _edges(draft)
    depth: dict[str, int] = {}

    def height(node: str) -> int:
        if node not in depth:
            depth[node] = 1 + max((height(p) for p in edges[node]), default=0)
        return depth[node]

    return max((height(n) for n in edges), default=0)


def validate_concept_questions(
    concept_id: str, catalog_tags: set[str], drafts: list[QuestionDraft]
) -> list[str]:
    errors: list[str] = []
    for role, want in QUESTIONS_PER_ROLE.items():
        got = sum(q.role == role for q in drafts)
        if got != want:
            errors.append(f"role_count: '{concept_id}' needs {want} '{role}' questions, got {got}")
    for i, q in enumerate(drafts, start=1):
        errors += [f"{e} (question {i})" for e in validate_question(q, catalog_tags)]
    return errors


def validate_question(q: QuestionDraft, catalog_tags: set[str]) -> list[str]:
    errors: list[str] = []
    if not q.prompt.strip():
        errors.append("empty_prompt: prompt is empty")
    if not q.explanation.strip():
        errors.append("empty_explanation: explanation is empty")
    wrong = [d.text.strip() for d in q.distractors]
    texts = [q.correct.strip(), *wrong]
    keys = texts  # exact text: in code topics "Hello" and "hello" are different answers
    if "" in keys:
        errors.append("empty_option: an option is empty")
    if len(set(keys)) < len(keys):
        errors.append("duplicate_option: two options have the same text")
    if any(BANNED_OPTION.search(t) for t in texts):
        errors.append("banned_option: 'all of the above' and 'none of the above' are not allowed")
    words = sorted({m.group(0).lower() for t in wrong for m in GIVEAWAY.finditer(t)})
    if words:
        errors.append(f"giveaway_word: reword the distractors that contain {words}")
    for d in q.distractors:
        if d.tag not in catalog_tags:
            errors.append(f"foreign_tag: '{d.tag}' is not in this concept's catalog")
    if len({d.tag for d in q.distractors}) < 2:
        errors.append("single_tag: the 3 distractors need at least 2 different catalog tags")
    correct, longest = len(texts[0]), max(len(t) for t in wrong)
    average = sum(len(t) for t in wrong) / len(wrong)
    if correct > longest and correct >= LONGEST_FACTOR * average and correct - average >= LONGEST_MIN_GAP:
        target = max(longest, math.ceil(LONGEST_FACTOR * average) - 1)
        errors.append(
            f"long_correct: correct option is {correct} chars but distractors average {average:.0f} "
            f"(longest {longest}); shorten it to at most {target} chars, or make the distractors "
            "equally specific and long"
        )
    return errors


def unused_tags(catalog_tags: set[str], drafts: list[QuestionDraft]) -> set[str]:
    return catalog_tags - {d.tag for q in drafts for d in q.distractors}


def validate_lesson_text(text: str) -> list[str]:
    errors: list[str] = []
    low, high = LESSON_WORDS
    words = len(text.split())
    if not low <= words <= high:
        errors.append(f"lesson_length: need {low} to {high} words, got {words}")
    if re.search(r"^\s*(#|[-*] )", text, re.MULTILINE):
        errors.append("lesson_format: plain prose only, no headings or bullet lists")
    return errors
