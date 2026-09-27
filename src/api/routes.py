from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import (
    get_new_data_use_case,
    get_question_use_case,
    get_remove_data_use_case,
    get_search_data_by_id_use_case,
    get_search_data_use_case,
)
from src.api.schemas import DataIn, DataOut, OkResponse, QuestionRequest, QuestionResponse, SearchRequest
from src.domain.data import Data
from src.use_cases.new_data import NewData
from src.use_cases.question import Question
from src.use_cases.remove_data import RemoveDataById
from src.use_cases.search_data import SearchDataById, SearchDataByListOfStr

router = APIRouter()


@router.post("/question", response_model=QuestionResponse)
async def ask_question(
    payload: QuestionRequest, use_case: Question = Depends(get_question_use_case)
) -> QuestionResponse:
    answer = await use_case.execute(payload.question)
    return QuestionResponse(answer=answer)


@router.post("/search", response_model=list[DataOut])
async def search_data(
    payload: SearchRequest, use_case: SearchDataByListOfStr = Depends(get_search_data_use_case)
) -> list[DataOut]:
    found = await use_case.execute(payload.really_questions)
    return [DataOut(id=item.id, source=item.source, content=item.content) for item in found]


@router.post("/data", response_model=OkResponse)
async def add_data(payload: DataIn, use_case: NewData = Depends(get_new_data_use_case)) -> OkResponse:
    data = Data(id=payload.id, source=payload.source, content=payload.content)
    ok = await use_case.execute(data)
    return OkResponse(ok=ok)


@router.get("/data/{id_}", response_model=DataOut)
async def get_data(id_: int, use_case: SearchDataById = Depends(get_search_data_by_id_use_case)) -> DataOut:
    data = await use_case.execute(id_)
    if data is None:
        raise HTTPException(status_code=404, detail="Data not found")
    return DataOut(id=data.id, source=data.source, content=data.content)


@router.delete("/data/{id_}", response_model=OkResponse)
async def delete_data(id_: int, use_case: RemoveDataById = Depends(get_remove_data_use_case)) -> OkResponse:
    ok = await use_case.execute(id_)
    return OkResponse(ok=ok)
