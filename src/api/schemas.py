from pydantic import BaseModel


class QuestionRequest(BaseModel):
    question: str


class QuestionResponse(BaseModel):
    answer: str


class SearchRequest(BaseModel):
    really_questions: list[str]


class DataIn(BaseModel):
    source: str
    content: str


class DataOut(BaseModel):
    id: int
    source: str
    content: str


class DataCreated(BaseModel):
    id: int


class OkResponse(BaseModel):
    ok: bool
