from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ConceptState(BaseModel):
    concept_id: str
    p_mastery: float = 0.2
    attempts: int = 0
    failed_rounds: int = 0
    stability_days: float = 0.0
    last_reviewed_at: datetime | None = None
    due_at: datetime | None = None
    lapses: int = 0
    explanations_tried: list[str] = []
    fallbacks: int = 0
    needs_help: bool = False


class MisconceptionState(BaseModel):
    tag: str
    concept_id: str
    status: Literal['suspected', 'confirmed', 'resolved'] = 'suspected'
    evidence: float = 0.0
    clean_streak: int = 0


class LearnerState(BaseModel):
    learner_id: str
    course_id: str
    concepts: dict[str, ConceptState] = Field(default_factory=dict)
    misconceptions: dict[str, MisconceptionState] = Field(default_factory=dict)
    roadmap: list[str] = Field(default_factory=list)
    session_questions: int = 0
    clock_offset_days: float = 0.0     # demo clock: how far this learner's "now" is shifted
    pending_step: 'Step | None' = None              # the stored decision; get_next runs once per decision
    pending_question_ids: list[str] = Field(default_factory=list)   # material built for pending_step
    served_question_ids: list[str] = Field(default_factory=list)    # ids /attempts accepts
    pending_lesson_key: str | None = None           # lesson cache key of the built material
    pending_built: bool = False                     # material for pending_step has been built


class BktParams(BaseModel):
    p_init: float = 0.2
    p_learn: float = 0.15
    p_slip: float = 0.1
    p_guess: float = 0.25         # 4-option MCQ
    mastery_threshold: float = 0.85


class PolicyConfig(BaseModel):
    adaptive: bool = True
    target_misconceptions: bool = True
    spaced_review: bool = True
    max_rounds_per_concept: int = 3
    max_questions_per_session: int = 15


class Step(BaseModel):
    kind: Literal['lesson', 'review', 'fallback', 'session_end', 'done']
    concept_id: str | None = None
    target_misconceptions: list[str] = []
    avoid_styles: list[str] = []
    difficulty: float | None = None
    target_concept: str | None = None
    give_up_after: bool = False


class AnswerIn(BaseModel):
    question_id: str
    chosen_index: int
    confidence: Literal['low', 'medium', 'high'] | None = None


class AnswerGraded(BaseModel):
    question_id: str
    concept_id: str
    correct: bool
    chosen_tag: str | None = None
    confidence: str | None = None