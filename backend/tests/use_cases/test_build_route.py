from src.repositories.json_campus_repository import JsonCampusRepository
from src.services.campus_service import CampusService
from src.use_cases.build_route import BuildRoute


def _use_case() -> BuildRoute:
    return BuildRoute(CampusService(JsonCampusRepository()))


async def test_builds_route_between_known_places() -> None:
    route = await _use_case().execute("kpp", "7-404")

    assert route is not None
    assert route.points[-1].floor == 4


async def test_default_source_is_kpp() -> None:
    route = await _use_case().execute(None, "7-404")

    assert route is not None
    assert route.from_label == "КПП"


async def test_returns_none_for_unknown_place() -> None:
    assert await _use_case().execute("kpp", "не-пойми-что") is None
