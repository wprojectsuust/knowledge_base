from pydantic import BaseModel, Field


class FactIn(BaseModel):
    field: str = Field(max_length=40, pattern=r"^[a-z_]+$")
    value: str = Field(min_length=1, max_length=200)


class HistoryTurnIn(BaseModel):
    question: str = Field(max_length=2000)
    answer: str = Field(max_length=6000)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    # последние реплики чата - хранятся только в браузере, сервер их нигде не сохраняет
    history: list[HistoryTurnIn] = Field(default_factory=list, max_length=10)
    # уже известные сведения о студенте (ответы на прошлые уточнения), фронт хранит их у себя
    facts: list[FactIn] = Field(default_factory=list, max_length=10)


class LocationOut(BaseModel):
    building: str
    room: str | None = None
    floor: int | None = None


class ClarificationOut(BaseModel):
    field: str
    question: str


class ImportReportOut(BaseModel):
    imported: int
    skipped: int
    failed: int


class RoutePointOut(BaseModel):
    x: float
    y: float
    floor: int
    building: str | None = None


class StreetRouteOut(BaseModel):
    """Тот же путь по улице - на карте пунктиром рядом с основным (через переходы)."""

    distance_m: float
    minutes: int
    points: list[RoutePointOut]


class RouteOut(BaseModel):
    campus: str
    from_label: str
    to_label: str
    steps: list[str]
    text: str
    distance_m: float
    minutes: int
    points: list[RoutePointOut]
    alternative: StreetRouteOut | None = None


class RouteRequestIn(BaseModel):
    source: str | None = Field(default=None, max_length=60)
    target: str = Field(max_length=60)


class QuestionResponse(BaseModel):
    # ровно одно из двух: либо ответ, либо просьба уточнить сведения о студенте
    answer: str | None = None
    clarification: ClarificationOut | None = None
    location: LocationOut | None = None
    route: RouteOut | None = None


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


def route_out(route) -> RouteOut:
    return RouteOut(
        campus=route.campus,
        from_label=route.from_label,
        to_label=route.to_label,
        steps=route.steps,
        text=route.text(),
        distance_m=round(route.distance_m, 1),
        minutes=route.minutes,
        points=_points(route.points),
        alternative=StreetRouteOut(
            distance_m=round(route.alternative.distance_m, 1),
            minutes=route.alternative.minutes,
            points=_points(route.alternative.points),
        )
        if route.alternative
        else None,
    )


def _points(points) -> list[RoutePointOut]:
    return [RoutePointOut(x=p.x, y=p.y, floor=p.floor, building=p.building) for p in points]
