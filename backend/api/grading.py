"""Pure helpers: grading, public question views, roadmap order. No I/O."""

from schemas.api import QuestionPublic
from schemas.content import ConceptGraph, Question
from schemas.learner import AnswerGraded, AnswerIn


class GradingError(ValueError):
    """An answer names an unknown question or an option that does not exist."""


def grade(questions: dict[str, Question], answers: list[AnswerIn]) -> list[AnswerGraded]:
    graded = []
    for a in answers:
        q = questions.get(a.question_id)
        if q is None:
            raise GradingError(f"unknown question '{a.question_id}'")
        if not 0 <= a.chosen_index < len(q.options):
            raise GradingError(f"chosen_index {a.chosen_index} out of range for '{a.question_id}'")
        graded.append(AnswerGraded(
            question_id=q.id,
            concept_id=q.concept_id,
            correct=a.chosen_index == q.correct_index,
            chosen_tag=q.options[a.chosen_index].misconception_tag,
            confidence=a.confidence,
        ))
    return graded


def to_public(q: Question) -> QuestionPublic:
    return QuestionPublic(id=q.id, concept_id=q.concept_id, prompt=q.prompt, options=[o.text for o in q.options])


def topo_order(graph: ConceptGraph) -> list[str]:
    """Prerequisites first; ties keep graph order. The graph is validated acyclic."""
    index = {c.id: i for i, c in enumerate(graph.concepts)}
    remaining = {c.id: set(c.prerequisites) for c in graph.concepts}
    order: list[str] = []
    while remaining:
        cid = min((c for c, pre in remaining.items() if not pre), key=index.__getitem__)
        order.append(cid)
        del remaining[cid]
        for pre in remaining.values():
            pre.discard(cid)
    return order


def pick_unseen_first(pool: list[Question], seen: set[str], n: int) -> list[Question]:
    """Unseen questions first (pool order), then seen ones if too few are left."""
    unseen = [q for q in pool if q.id not in seen]
    return (unseen + [q for q in pool if q.id in seen])[:n]
