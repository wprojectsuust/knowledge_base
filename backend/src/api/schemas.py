from pydantic import BaseModel


class QuestionRequest(BaseModel):
    question: str


class QuestionResponse(BaseModel):
    answer: str


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
