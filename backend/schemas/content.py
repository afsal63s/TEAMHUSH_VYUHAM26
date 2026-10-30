from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# Learner's self-assessed level, picked from a dropdown when creating a course.
Level = Literal['novice', 'beginner', 'intermediate', 'advanced']


class Concept(BaseModel):
    id: str
    name: str
    description: str
    prerequisites: list[str] = []


class MisconceptionDef(BaseModel):
    tag: str                      # stable id, e.g. 'loops__off_by_one'
    concept_id: str
    description: str


class ConceptGraph(BaseModel):
    topic: str
    concepts: list[Concept]
    misconceptions: list[MisconceptionDef]

    @model_validator(mode='after')
    def validate_graph(self) -> 'ConceptGraph':
        concept_ids = {c.id for c in self.concepts}

        # 1. Prerequisites must exist in the graph
        for c in self.concepts:
            for prereq in c.prerequisites:
                if prereq not in concept_ids:
                    raise ValueError(f"Prerequisite '{prereq}' for concept '{c.id}' does not exist.")

        # 2. Graph must be acyclic (DFS check)
        adj = {c.id: c.prerequisites for c in self.concepts}
        visited: set[str] = set()
        stack: set[str] = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            stack.add(node)
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in stack:
                    return True
            stack.remove(node)
            return False

        for node in concept_ids:
            if node not in visited:
                if has_cycle(node):
                    raise ValueError("Concept graph contains a cycle. Prerequisites must be acyclic.")

        return self


class Option(BaseModel):
    text: str
    misconception_tag: str | None = None   # None ONLY on the correct option


class Question(BaseModel):
    id: str
    course_id: str
    concept_id: str
    kind: Literal['diagnostic', 'practice', 'review', 'transfer']
    prompt: str
    options: list[Option]
    correct_index: int
    explanation: str
    difficulty: float = Field(ge=0, le=1)
    variant_of: str | None = None

    @model_validator(mode='after')
    def validate_question(self) -> 'Question':
        if len(self.options) != 4:
            raise ValueError(f"Question must have exactly 4 options, got {len(self.options)}.")

        if not (0 <= self.correct_index < len(self.options)):
            raise ValueError(f"correct_index {self.correct_index} is out of range.")

        if self.options[self.correct_index].misconception_tag is not None:
            raise ValueError("The correct option must not have a misconception_tag.")

        for i, option in enumerate(self.options):
            if i != self.correct_index and option.misconception_tag is None:
                raise ValueError(f"Distractor at index {i} must have a misconception_tag.")

        return self


class Resource(BaseModel):
    """A web article or video the research agent found for a concept."""
    kind: Literal['article', 'video']
    title: str
    url: str
    snippet: str = ""


class Lesson(BaseModel):
    concept_id: str
    style: str                    # e.g. 'analogy', 'worked_example', 'contrast'
    explanation: str
    targets: list[str] = []       # misconception tags addressed
    resources: list[Resource] = []  # filled by the research agent (empty until then)


class Course(BaseModel):
    """The stored course record. Questions live in their own collection."""
    course_id: str
    prompt: str
    level: Level = 'beginner'
    topic: str
    graph: ConceptGraph
    created_at: datetime
    deadline: datetime | None = None
    status: Literal['generating', 'ready', 'failed'] = 'ready'
    question_count: int = 0