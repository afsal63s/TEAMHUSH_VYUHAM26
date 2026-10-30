from pydantic import BaseModel

from schemas.content import ConceptGraph, Level, Question


class CourseBundle(BaseModel):
    course_id: str
    prompt: str
    level: Level
    graph: ConceptGraph
    questions: list[Question]
