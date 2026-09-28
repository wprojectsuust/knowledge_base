import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from src.api.dependencies import (
    get_build_route_use_case,
    get_campus_service,
    get_new_data_use_case,
    get_question_use_case,
    get_remove_data_use_case,
    get_resolve_location_use_case,
    get_search_data_by_id_use_case,
    get_search_data_use_case,
)
from src.api.schemas import (
    ClarificationOut,
    DataCreated,
    DataIn,
    DataOut,
    LocationOut,
    OkResponse,
    QuestionRequest,
    QuestionResponse,
    RouteOut,
    RouteRequestIn,
    SearchRequest,
    route_out,
)
from src.domain.campus import Route, generate_rooms
from src.domain.clarification import ClarificationRequest, KnownFact
from src.domain.data import Data
from src.domain.division import divisions_by_slug
from src.services.campus_service import CampusService
from src.use_cases.build_route import BuildRoute
from src.use_cases.new_data import NewData
from src.use_cases.question import Question
from src.use_cases.remove_data import RemoveDataById
from src.use_cases.resolve_location import ResolveLocation
from src.use_cases.search_data import SearchDataById, SearchDataByListOfStr

logger = logging.getLogger(__name__)

router = APIRouter()

_UPLOAD_PAGE_HTML = (Path(__file__).resolve().parent / "static" / "index.html").read_text(encoding="utf-8")


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def upload_page() -> HTMLResponse:
    return HTMLResponse(content=_UPLOAD_PAGE_HTML)


@router.post("/question", response_model=QuestionResponse)
async def ask_question(
    payload: QuestionRequest,
    use_case: Question = Depends(get_question_use_case),
    resolve_location: ResolveLocation = Depends(get_resolve_location_use_case),
) -> QuestionResponse:
    logger.info("POST /question: %s (известно полей: %d)", payload.question, len(payload.facts))
    facts = [KnownFact(field=fact.field, value=fact.value) for fact in payload.facts]
    answer = await use_case.execute(payload.question, facts)
    if isinstance(answer, ClarificationRequest):
        logger.info("POST /question: нужно уточнение поля %s", answer.field)
        return QuestionResponse(clarification=ClarificationOut(field=answer.field, question=answer.question))
    if isinstance(answer, Route):
        logger.info("POST /question: маршрут %s -> %s", answer.from_label, answer.to_label)
        return QuestionResponse(answer=answer.text(), route=route_out(answer))

    # место считаем от готового ответа, а не храним в кэше: вычисляется детерминированно и дёшево
    location = await resolve_location.execute(payload.question, answer)
    logger.info("POST /question: ответ готов (%d символов), место=%s", len(answer), location)
    return QuestionResponse(
        answer=answer,
        location=LocationOut(building=location.building, room=location.room, floor=location.floor)
        if location
        else None,
    )


@router.post("/search", response_model=list[DataOut])
async def search_data(
    payload: SearchRequest, use_case: SearchDataByListOfStr = Depends(get_search_data_use_case)
) -> list[DataOut]:
    logger.info("POST /search: вопросы=%s, division=%s", payload.really_questions, payload.division)
    if payload.division is not None and payload.division not in divisions_by_slug():
        raise HTTPException(status_code=422, detail=f"Неизвестный division slug: {payload.division}")
    found = await use_case.execute(payload.really_questions, division=payload.division)
    logger.info("POST /search: найдено %d документов (id=%s)", len(found), [item.id for item in found])
    return [DataOut(id=item.id, source=item.source, content=item.content, division=item.division) for item in found]


@router.post("/data", response_model=DataCreated)
async def add_data(payload: DataIn, use_case: NewData = Depends(get_new_data_use_case)) -> DataCreated:
    logger.info(
        "POST /data: источник=%s, длина контента=%d, division=%s", payload.source, len(payload.content), payload.division
    )
    if payload.division is not None and payload.division not in divisions_by_slug():
        raise HTTPException(status_code=422, detail=f"Неизвестный division slug: {payload.division}")
    data = Data(source=payload.source, content=payload.content, division=payload.division)
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
    return DataOut(id=data.id, source=data.source, content=data.content, division=data.division)


@router.delete("/data/{id_}", response_model=OkResponse)
async def delete_data(id_: int, use_case: RemoveDataById = Depends(get_remove_data_use_case)) -> OkResponse:
    logger.info("DELETE /data/%s", id_)
    ok = await use_case.execute(id_)
    return OkResponse(ok=ok)


@router.get("/campus")
async def get_campuses(campus_service: CampusService = Depends(get_campus_service)) -> list[dict]:
    """Данные для 3D-карты: корпуса, переходы, лестницы, места, входы, улицы + раскладка кабинетов.
    Кабинеты компактно: {корпус: [[номер, этаж, x1, y1, x2, y2, подпись|null], ...]}."""
    result = []
    for campus in campus_service.list():
        result.append(
            {
                "id": campus.id,
                "title": campus.title,
                "address": campus.address,
                "scale": campus.scale,
                "buildings": [
                    {"id": b.id, "name": b.name, "label": b.label, "floors": b.floors, "wings": b.wings}
                    for b in campus.buildings
                ],
                "bridges": [
                    {"from": b.from_building, "to": b.to_building, "floors": b.floors, "rect": b.rect}
                    for b in campus.bridges
                ],
                "stairs": [{"building": s.building, "at": s.at} for s in campus.stairs],
                "places": [
                    {"id": p.id, "kind": p.kind, "building": p.building, "floor": p.floor, "label": p.label, "at": p.at}
                    for p in campus.places
                ],
                "entrances": [{"building": e.building, "at": e.at, "dir": e.dir} for e in campus.entrances],
                "streets": [{"name": s.name, "rect": s.rect} for s in campus.streets],
                "rooms": {
                    b.id: [
                        [r.number, r.floor, *(round(v, 1) for v in r.rect), r.label]
                        for r in generate_rooms(campus, b)
                    ]
                    for b in campus.buildings
                },
            }
        )
    return result


@router.post("/route", response_model=RouteOut)
async def build_route(payload: RouteRequestIn, use_case: BuildRoute = Depends(get_build_route_use_case)) -> RouteOut:
    logger.info("POST /route: %s -> %s", payload.source, payload.target)
    route = await use_case.execute(payload.source, payload.target)
    if route is None:
        raise HTTPException(status_code=404, detail="Не удалось построить маршрут: место не найдено на карте")
    return route_out(route)
