from datetime import datetime

from pydantic import BaseModel

from schemas.content import Level, Lesson
from schemas.learner import AnswerGraded, AnswerIn, ConceptState, MisconceptionState, Step


class CreateCourseIn(BaseModel):
    prompt: str
    level: Level = 'beginner'
    deadline: datetime | None = None


class CreateCourseOut(BaseModel):
    course_id: str
    status: str
    topic: str = ""
    concepts: list[dict] = []        # [{id, name, prerequisites}] for the UI graph


class QuestionPublic(BaseModel):     # strips answers, tags and explanations before grading
    id: str
    concept_id: str
    prompt: str
    options: list[str]


class StartOut(BaseModel):
    questions: list[QuestionPublic]  # the diagnostic: 1 question per concept


class SubmitAnswersIn(BaseModel):
    answers: list[AnswerIn]


class StepOut(BaseModel):
    step: Step
    reason: str = ""                 # built from facts, e.g. "off_by_one confirmed (evidence 4)"
    lesson: Lesson | None = None
    questions: list[QuestionPublic] = []


class AttemptResultOut(BaseModel):
    graded: list[AnswerGraded]
    correct_indices: dict[str, int]  # question_id -> index, safe to send after grading
    explanations: dict[str, str]
    mastery: dict[str, float]
    new_confirmed_misconceptions: list[str]
    messages: list[str] = []         # encouragement, rule-based
    next: StepOut


class MasteryOut(BaseModel):
    concepts: list[ConceptState]
    misconceptions: list[MisconceptionState]
    next_due: datetime | None = None
    due: dict[str, datetime] = {}    # concept_id -> due time
    roadmap: list[str] = []
    needs_help: list[str] = []
    days_left: int | None = None
    gaps: list[str] = []             # concepts not yet mastered, in roadmap order
    retrievability: dict[str, float] = {}   # concept_id -> current recall probability
    pace: dict[str, float] = {}      # {"mastered": n, "total": n, "attempts_per_mastered": x}


class AdvanceIn(BaseModel):
    days: int


class AdvanceOut(BaseModel):
    now: datetime                    # the learner's simulated "now"
    due_now: list[str]               # concepts due for review
    next_kind: str | None = None     # the decision stored for GET .../next
    next_concept_id: str | None = None