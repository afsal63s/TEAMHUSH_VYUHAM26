"""Shapes the LLM fills in. Code turns them into the final schemas.content models."""

from typing import Literal

from pydantic import BaseModel, Field

QuestionRole = Literal["diagnostic", "practice", "transfer"]


class MisconceptionDraft(BaseModel):
    slug: str = Field(description="short snake_case name for the wrong belief")
    description: str = Field(description='one sentence: "believes X, but actually Y"')


class ConceptDraft(BaseModel):
    id: str = Field(description="unique snake_case slug")
    name: str
    description: str
    prerequisites: list[str] = Field(description="ids of concepts this one cannot be understood without")
    misconceptions: list[MisconceptionDraft]


class GraphDraft(BaseModel):
    topic: str
    concepts: list[ConceptDraft]


class DistractorDraft(BaseModel):
    text: str
    tag: str = Field(description="a tag copied exactly from the concept's misconception catalog")


class QuestionDraft(BaseModel):
    role: QuestionRole
    difficulty: float
    prompt: str
    correct: str
    distractors: list[DistractorDraft] = Field(min_length=3, max_length=3)
    explanation: str


class QuestionsDraft(BaseModel):
    questions: list[QuestionDraft]


class LessonDraft(BaseModel):
    explanation: str
