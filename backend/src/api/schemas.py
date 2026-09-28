from pydantic import BaseModel, Field


class FactIn(BaseModel):
    field: str = Field(max_length=40, pattern=r"^[a-z_]+$")
    value: str = Field(min_length=1, max_length=200)


class QuestionRequest(BaseModel):
    question: str
    # уже известные сведения о студенте (ответы на прошлые уточнения), фронт хранит их у себя
    facts: list[FactIn] = Field(default_factory=list, max_length=10)


class LocationOut(BaseModel):
    building: str
    room: str | None = None
    floor: int | None = None


class ClarificationOut(BaseModel):
    field: str
    question: str


class QuestionResponse(BaseModel):
    # ровно одно из двух: либо ответ, либо просьба уточнить сведения о студенте
    answer: str | None = None
    clarification: ClarificationOut | None = None
    location: LocationOut | None = None


class SearchRequest(BaseModel):
    really_questions: list[str]
    division: str | None = None


class DataIn(BaseModel):
    source: str
    content: str
    division: str | None = None


class DataOut(BaseModel):
    id: int
    source: str
    content: str
    division: str | None = None


class DataCreated(BaseModel):
    id: int


class OkResponse(BaseModel):
    ok: bool
