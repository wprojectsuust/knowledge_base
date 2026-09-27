import logging

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import (
    get_new_data_use_case,
    get_question_use_case,
    get_remove_data_use_case,
    get_search_data_by_id_use_case,
    get_search_data_use_case,
)
from src.api.schemas import DataCreated, DataIn, DataOut, OkResponse, QuestionRequest, QuestionResponse, SearchRequest
from src.domain.data import Data
from src.use_cases.new_data import NewData
from src.use_cases.question import Question
from src.use_cases.remove_data import RemoveDataById
from src.use_cases.search_data import SearchDataById, SearchDataByListOfStr

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/question", response_model=QuestionResponse)
async def ask_question(
    payload: QuestionRequest, use_case: Question = Depends(get_question_use_case)
) -> QuestionResponse:
    logger.info("POST /question: %s", payload.question)
    answer = await use_case.execute(payload.question)
    logger.info("POST /question: ответ готов (%d символов)", len(answer))
    return QuestionResponse(answer=answer)


@router.post("/search", response_model=list[DataOut])
async def search_data(
    payload: SearchRequest, use_case: SearchDataByListOfStr = Depends(get_search_data_use_case)
) -> list[DataOut]:
    logger.info("POST /search: вопросы=%s", payload.really_questions)
    found = await use_case.execute(payload.really_questions)
    logger.info("POST /search: найдено %d документов (id=%s)", len(found), [item.id for item in found])
    return [DataOut(id=item.id, source=item.source, content=item.content) for item in found]


@router.post("/data", response_model=DataCreated)
async def add_data(payload: DataIn, use_case: NewData = Depends(get_new_data_use_case)) -> DataCreated:
    logger.info("POST /data: источник=%s, длина контента=%d", payload.source, len(payload.content))
    data = Data(source=payload.source, content=payload.content)
    new_id = await use_case.execute(data)
    if new_id is None:
        logger.warning("POST /data: не удалось проиндексировать данные из источника %s", payload.source)
        raise HTTPException(status_code=422, detail="Не удалось проиндексировать данные")
    logger.info("POST /data: создано id=%d", new_id)
    return DataCreated(id=new_id)


@router.get("/data/{id_}", response_model=DataOut)
async def get_data(id_: int, use_case: SearchDataById = Depends(get_search_data_by_id_use_case)) -> DataOut:
    logger.info("GET /data/%s", id_)
    data = await use_case.execute(id_)
    if data is None:
        logger.info("GET /data/%s: не найдено", id_)
        raise HTTPException(status_code=404, detail="Data not found")
    return DataOut(id=data.id, source=data.source, content=data.content)


@router.delete("/data/{id_}", response_model=OkResponse)
async def delete_data(id_: int, use_case: RemoveDataById = Depends(get_remove_data_use_case)) -> OkResponse:
    logger.info("DELETE /data/%s", id_)
    ok = await use_case.execute(id_)
    return OkResponse(ok=ok)
