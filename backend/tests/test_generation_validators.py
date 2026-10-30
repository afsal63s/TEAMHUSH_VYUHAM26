import asyncio

import pytest

from generation import prompts
from generation import validators as v
from generation.course_gen import build_graph, build_questions, generate_validated, namespace_tags, shuffle_options
from generation.drafts import ConceptDraft, DistractorDraft, GraphDraft, MisconceptionDraft, QuestionDraft, QuestionsDraft
from generation.styles import choose_style
from schemas.content import Option

TAGS = {"loops__a", "loops__b", "loops__c"}


def concept(cid: str, prereqs: list[str] | None = None, n_misc: int = 3) -> ConceptDraft:
    return ConceptDraft(
        id=cid, name=cid, description="d", prerequisites=prereqs or [],
        misconceptions=[MisconceptionDraft(slug=f"m{i}", description="x") for i in range(n_misc)],
    )


def good_graph() -> GraphDraft:
    # roots c0 and c1; longest chain c0 -> c2 -> c4 -> c6 -> c7 is 5 of 8 concepts
    return GraphDraft(topic="t", concepts=[
        concept("c0"), concept("c1"), concept("c2", ["c0"]), concept("c3", ["c1"]),
        concept("c4", ["c2"]), concept("c5", ["c3"]), concept("c6", ["c4", "c5"]), concept("c7", ["c6"]),
    ])


def distractors(texts: list[str], tags: list[str]) -> list[DistractorDraft]:
    return [DistractorDraft(text=t, tag=g) for t, g in zip(texts, tags)]


def question(role: str = "diagnostic", **over) -> QuestionDraft:
    base = dict(
        role=role, difficulty=0.3, prompt="Why?", correct="right",
        distractors=distractors(["wrong0", "wrong1", "wrong2"], sorted(TAGS)), explanation="because",
    )
    return QuestionDraft(**{**base, **over})


def good_questions() -> list[QuestionDraft]:
    return [question("diagnostic")] * 3 + [question("practice")] * 2 + [question("transfer")] * 2


def checks(errors: list[str]) -> set[str]:
    return {e.split(":", 1)[0] for e in errors}


# graph


def test_good_graph_passes():
    assert v.validate_graph_draft(good_graph()) == []


def test_concept_count():
    g = good_graph()
    g.concepts = g.concepts[:7]
    assert "concept_count" in checks(v.validate_graph_draft(g))


def test_cycle_and_unknown_prerequisite():
    g = good_graph()
    g.concepts[1].prerequisites = ["c7"]  # c1 -> c7 -> c6 -> c5 -> c3 -> c1
    assert "cycle" in checks(v.validate_graph_draft(g))
    g = good_graph()
    g.concepts[2].prerequisites = ["nope"]
    assert "unknown_prerequisite" in checks(v.validate_graph_draft(g))


def test_root_count_and_flat_graph():
    flat = GraphDraft(topic="t", concepts=[concept(f"c{i}") for i in range(8)])
    assert {"root_count", "flat_graph"} <= checks(v.validate_graph_draft(flat))
    one_root = good_graph()
    one_root.concepts[1].prerequisites = ["c0"]
    assert "root_count" in checks(v.validate_graph_draft(one_root))


def test_longest_chain():
    assert v.longest_chain(good_graph()) == 5
    line = GraphDraft(topic="t", concepts=[concept("c0"), concept("c1")] + [concept(f"c{i}", [f"c{i - 1}"]) for i in range(2, 8)])
    assert v.longest_chain(line) == 7
    assert "long_chain" in checks(v.validate_graph_draft(line))


def test_misconception_rules():
    g = good_graph()
    g.concepts[0].misconceptions = g.concepts[0].misconceptions[:2]
    assert "few_misconceptions" in checks(v.validate_graph_draft(g))
    g = good_graph()
    g.concepts[0].misconceptions[1].slug = "M0"  # normalises to m0, same as the first
    assert "duplicate_tag" in checks(v.validate_graph_draft(g))


def test_ids():
    g = good_graph()
    g.concepts[1].id = "c0"
    assert "duplicate_id" in checks(v.validate_graph_draft(g))
    g = good_graph()
    g.concepts[0].id = "Bad Id"
    assert "bad_id" in checks(v.validate_graph_draft(g))


def test_build_graph_namespaces_tags():
    graph = build_graph(good_graph(), "prompt")
    tags = [m.tag for m in graph.misconceptions]
    assert len(tags) == len(set(tags)) == 24
    assert all(m.tag.startswith(f"{m.concept_id}__") for m in graph.misconceptions)


# questions


def test_good_questions_pass():
    assert v.validate_concept_questions("loops", TAGS, good_questions()) == []


def test_role_counts():
    assert "role_count" in checks(v.validate_concept_questions("loops", TAGS, good_questions()[:6]))


@pytest.mark.parametrize(
    "override, check",
    [
        ({"prompt": "  "}, "empty_prompt"),
        ({"correct": "wrong0"}, "duplicate_option"),
        ({"correct": "None of the above"}, "banned_option"),
        ({"distractors": distractors(["wrong0", "wrong1", "wrong2"], ["x__a", "x__b", "x__c"])}, "foreign_tag"),
    ],
)
def test_question_failures(override, check):
    assert check in checks(v.validate_question(question(**override), TAGS))

def test_giveaway_words():
    for word in ("always", "never", "guarantees"):
        bad = distractors([f"It {word.upper()} works", "wrong1", "wrong2"], sorted(TAGS))
        assert "giveaway_word" in checks(v.validate_question(question(distractors=bad), TAGS))
    # allowed in the correct option; "alwaysly" is not the word "always"
    ok = question(correct="It must", distractors=distractors(["alwaysly", "wrong1", "wrong2"], sorted(TAGS)))
    assert "giveaway_word" not in checks(v.validate_question(ok, TAGS))


def test_distinct_tags():
    one = distractors(["wrong0", "wrong1", "wrong2"], ["loops__a"] * 3)
    assert "single_tag" in checks(v.validate_question(question(distractors=one), TAGS))
    two = distractors(["wrong0", "wrong1", "wrong2"], ["loops__a", "loops__a", "loops__b"])
    assert "single_tag" not in checks(v.validate_question(question(distractors=two), TAGS))


def test_long_correct():
    errors = v.validate_question(question(correct="x" * 30), TAGS)  # distractors are 6 chars
    [error] = [e for e in errors if e.startswith("long_correct")]
    assert "is 30 chars" in error and "average 6" in error and "at most 8 chars" in error
    assert "long_correct" not in checks(v.validate_question(question(correct="x" * 8), TAGS))
    not_longest = question(correct="x" * 30, distractors=distractors(["y" * 40, "wrong1", "wrong2"], sorted(TAGS)))
    assert "long_correct" not in checks(v.validate_question(not_longest, TAGS))


def test_unused_tags():
    same = question(distractors=distractors(["wrong0", "wrong1", "wrong2"], ["loops__a"] * 3))
    assert v.unused_tags(TAGS, [same]) == {"loops__b", "loops__c"}
    assert v.unused_tags(TAGS, good_questions()) == set()


# lessons and styles


def test_lesson_text():
    assert v.validate_lesson_text(" ".join(["word"] * 150)) == []
    assert "lesson_length" in checks(v.validate_lesson_text("too short"))
    assert "lesson_format" in checks(v.validate_lesson_text("# Title\n" + " ".join(["w"] * 150)))
    assert "lesson_format" in checks(v.validate_lesson_text("- point\n" + " ".join(["w"] * 150)))


def test_choose_style():
    every = ["contrast", "worked_example", "analogy", "step_by_step"]
    assert choose_style([], True) == "contrast"
    assert choose_style([], False) == "worked_example"
    assert choose_style(["contrast"], True) == "worked_example"
    assert choose_style(["worked_example"], False) == "contrast"
    assert choose_style(["contrast", "worked_example"], True) == "analogy"
    assert choose_style(every[:3], False) == "step_by_step"
    assert choose_style(every, True) == "contrast"
    assert choose_style(every, False) == "worked_example"


# post-processing and retries


def test_shuffle_keeps_correct_option_and_tags():
    options = [Option(text="right"), *(Option(text=f"w{i}", misconception_tag=f"t{i}") for i in range(3))]
    shuffled, idx = shuffle_options("qid-1", options, 0)
    assert shuffled[idx].text == "right" and shuffled[idx].misconception_tag is None
    assert {(o.text, o.misconception_tag) for o in shuffled} == {(o.text, o.misconception_tag) for o in options}
    assert shuffle_options("qid-1", options, 0) == (shuffled, idx)  # deterministic per id


def test_build_questions():
    qs = build_questions("abc12345", "loops", good_questions())
    assert [q.id for q in qs] == [f"abc12345-loops-{x}" for x in ("d1", "d2", "d3", "p1", "p2", "t1", "t2")]
    assert all(q.options[q.correct_index].text == "right" for q in qs)
    assert {q.kind for q in qs} == {"diagnostic", "practice", "transfer"}


def test_retry_repairs_previous_reply():
    seen: list[tuple[list[str], str | None]] = []
    replies = [question(prompt="first"), question(prompt="second")]

    async def call(errors, previous):
        seen.append((errors, previous))
        return replies.pop(0)

    result = asyncio.run(generate_validated("t", call, lambda q: ["bad: x"] if q.prompt == "first" else []))
    assert result.prompt == "second"
    assert seen[0] == ([], None)
    assert seen[1][0] == ["bad: x"] and '"prompt":"first"' in seen[1][1]
    suffix = prompts.retry_suffix(["bad: x"], seen[1][1])
    assert "<previous>" in suffix and "Keep every part that passed unchanged" in suffix
    assert prompts.retry_suffix([], "ignored") == ""


def test_namespace_tags_maps_bare_slugs_only():
    q = question(distractors=distractors(["wrong0", "wrong1", "wrong2"], ["a", "loops__b", "Other Thing"]))
    fixed = namespace_tags("loops", TAGS, QuestionsDraft(questions=[q]))
    assert [d.tag for d in fixed.questions[0].distractors] == ["loops__a", "loops__b", "Other Thing"]
    assert "foreign_tag" in checks(v.validate_question(fixed.questions[0], TAGS))  # unknown stays unknown


# learner level


def test_difficulty_ranges_shift_with_level():
    from generation.course_gen import difficulty_ranges

    assert difficulty_ranges("beginner") == {"diagnostic": (0.2, 0.5), "practice": (0.5, 0.8), "transfer": (0.5, 0.8)}
    assert difficulty_ranges("novice")["diagnostic"] == (0.1, 0.4)
    assert difficulty_ranges("intermediate")["practice"] == (0.6, 0.9)
    assert difficulty_ranges("advanced")["transfer"] == (0.7, 0.95)  # capped below 1


def test_build_questions_clamps_difficulty_to_level():
    qs = build_questions("abc12345", "loops", [question("diagnostic", difficulty=0.3)], "advanced")
    assert qs[0].difficulty == 0.4  # advanced diagnostic range starts at 0.4
    qs = build_questions("abc12345", "loops", [question("practice", difficulty=0.9)], "novice")
    assert qs[0].difficulty == 0.7  # novice practice range ends at 0.7


def test_prompts_carry_level():
    from generation.course_gen import difficulty_ranges
    from schemas.content import Concept

    graph_text = prompts.graph_user("Python", "advanced", None, [], None)
    assert "advanced" in graph_text and prompts.LEVEL_GUIDE["advanced"] in graph_text
    c = Concept(id="loops", name="Loops", description="d")
    q_text = prompts.questions_user("Python", c, [], "novice", difficulty_ranges("novice"), [], None)
    assert "novice" in q_text and "diagnostic 0.10 to 0.40" in q_text


def test_create_course_level_is_a_fixed_choice():
    from pydantic import ValidationError

    from schemas.api import CreateCourseIn

    assert CreateCourseIn(prompt="python").level == "beginner"
    assert CreateCourseIn(prompt="python", level="novice").level == "novice"
    with pytest.raises(ValidationError):
        CreateCourseIn(prompt="python", level="expert")


def test_duplicate_option_is_case_sensitive():
    case = question(correct="Hello", distractors=distractors(["hello", "HELLO", "wrong2"], sorted(TAGS)))
    assert "duplicate_option" not in checks(v.validate_question(case, TAGS))
    spaced = question(correct="wrong0 ", distractors=distractors(["wrong0", "wrong1", "wrong2"], sorted(TAGS)))
    assert "duplicate_option" in checks(v.validate_question(spaced, TAGS))


def test_long_correct_ignores_short_options():
    short = question(correct="123", distractors=distractors(["1", "2", "4"], sorted(TAGS)))  # 3x, but 2 chars
    assert "long_correct" not in checks(v.validate_question(short, TAGS))
