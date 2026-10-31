from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from schemas.content import Level, Lesson, Resource
from schemas.learner import AnswerGraded, AnswerIn, ConceptState, HistoryPoint, MisconceptionState, Step


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
    skipped: list[str] = []          # served question ids not answered in this round (no effect)


class ReviewMark(BaseModel):
    at: datetime
    passed: bool


class ConceptStateOut(ConceptState):     # /state: a concept plus its last 20 reviews
    reviews: list[ReviewMark] = []


class MisconceptionOut(MisconceptionState):   # /state: a misconception plus its catalog description
    description: str = ""


class Retention(BaseModel):
    reviews_total: int = 0
    reviews_passed: int = 0
    review_pass_rate: float | None = None      # null when there are no reviews
    delayed_reviews_total: int = 0
    delayed_pass_rate: float | None = None     # null when there are no delayed reviews
    delayed_threshold_days: int = 7


class MasteryOut(BaseModel):
    concepts: list[ConceptStateOut]
    misconceptions: list[MisconceptionOut]
    next_due: datetime | None = None
    due: dict[str, datetime] = {}    # concept_id -> due time
    roadmap: list[str] = []
    needs_help: list[str] = []
    days_left: int | None = None
    gaps: list[str] = []             # concepts not yet mastered, in roadmap order
    retrievability: dict[str, float] = {}   # concept_id -> current recall probability
    pace: dict[str, float] = {}      # {"mastered": n, "total": n, "attempts_per_mastered": x}
    now: datetime | None = None      # the learner's simulated now
    history: list[HistoryPoint] = []  # progress samples, oldest first (last 500)
    learning_rate: float = 0.0       # mean change in avg_mastery per answered question, last 10 answers
    avg_stability_days: float = 0.0  # mean over concepts with stability > 0
    stability: dict[str, float] = {}  # concept_id -> stability_days
    retention: Retention = Retention()   # review pass rates, overall and after >= 7 days


class AdvanceIn(BaseModel):
    days: int


class AdvanceOut(BaseModel):
    now: datetime                    # the learner's simulated "now"
    due_now: list[str]               # concepts due for review
    next_kind: str | None = None     # the decision stored for GET .../next
    next_concept_id: str | None = None


class ConceptResearch(BaseModel):    # GET .../resources: one entry per gap concept being researched
    status: Literal['pending', 'ready', 'failed'] = 'pending'
    resources: list[Resource] = []


class AuthCheckOut(BaseModel):
    ok: bool = True


class CourseSummary(BaseModel):      # GET /courses: one card per course for the dashboard (no graph)
    course_id: str
    topic: str
    level: Level
    status: str
    created_at: datetime
    deadline: datetime | None = None
    concept_count: int = 0
    started: bool = False
    mastered: int = 0
    avg_mastery: float = 0.0
    avg_retrievability: float = 0.0
    next_due_at: datetime | None = None
    overdue_count: int = 0
    needs_help_count: int = 0
    last_activity_at: datetime | None = None   # simulated time of the last history point


class DueItem(BaseModel):            # GET /due: one scheduled review
    course_id: str
    topic: str
    concept_id: str
    concept_name: str
    due_at: datetime
    overdue_days: float = 0.0        # 0 if not yet due (learner's simulated clock)
    retrievability: float = 1.0


class ResetOut(BaseModel):
    ok: bool = True
