import pytest

from src.domain.campus import CampusNavigator, RouteTarget, parse_target
from src.repositories.json_campus_repository import JsonCampusRepository


@pytest.fixture(scope="module")
def navigator() -> CampusNavigator:
    return CampusNavigator(JsonCampusRepository().get("ugatu"))


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("kpp", RouteTarget(kind="kpp")),
        ("КПП", RouteTarget(kind="kpp")),
        ("7-404", RouteTarget(kind="room", building="7", room="404")),
        ("3-106Б", RouteTarget(kind="room", building="3", room="106б")),
        ("7", RouteTarget(kind="building", building="7")),
        ("sport", RouteTarget(kind="building", building="sport")),
        ("7@3", RouteTarget(kind="floor", building="7", floor=3)),
        ("place:library", RouteTarget(kind="place", place="library")),
        ("place:cafe", RouteTarget(kind="place", place="cafe")),
    ],
)
def test_parse_target(spec, expected) -> None:
    assert parse_target(spec) == expected


def test_parse_target_rejects_garbage() -> None:
    assert parse_target("куда-нибудь") is None


def test_rooms_are_generated_with_isu_numbering_and_known_rooms_in_place(navigator) -> None:
    rooms = navigator.rooms("1")
    first_floor = [room for room in rooms if room.floor == 1]

    numbers = [room.number for room in first_floor]
    assert len(numbers) == len(set(numbers))  # без дублей на этаже
    assert all(number.startswith("1") for number in numbers)
    assert next(room for room in first_floor if room.number == "125").label == "Медпункт"
    assert any(room.number == "404" and room.floor == 4 for room in navigator.rooms("7"))


def test_route_from_kpp_to_room_goes_up_to_its_floor(navigator) -> None:
    route = navigator.route(parse_target("kpp"), parse_target("7-404"))

    assert route is not None
    assert route.points[-1].floor == 4
    assert route.points[0].floor == 0  # старт на улице у КПП
    assert route.distance_m > 0
    text = "\n".join(route.steps)
    assert "КПП" in text
    assert "4 этаж" in text
    assert "7-404" in text


def test_route_between_buildings_changes_floor_and_building(navigator) -> None:
    route = navigator.route(parse_target("7-404"), parse_target("1-101"))

    assert route is not None
    assert route.points[0].floor == 4
    assert route.points[-1].floor == 1
    assert {point.building for point in route.points if point.building} >= {"7", "1"}


def test_route_to_any_cafe_ends_at_a_cafe(navigator) -> None:
    route = navigator.route(parse_target("kpp"), parse_target("place:cafe"))

    assert route is not None
    assert "Буфет" in route.to_label


def test_stairs_are_collapsed_into_one_step(navigator) -> None:
    route = navigator.route(parse_target("kpp"), parse_target("9@7"))

    assert route is not None
    stair_steps = [step for step in route.steps if "лестниц" in step]
    # несколько пролётов подряд - одна фраза, а не шаг на каждый этаж
    assert len(stair_steps) <= 2


def test_outdoor_legs_do_not_cross_buildings(navigator) -> None:
    route = navigator.route(parse_target("kpp"), parse_target("3-201"))

    assert route is not None
    for a, b in zip(route.points, route.points[1:]):
        if a.floor == 0 and b.floor == 0:
            assert navigator.segment_is_clear((a.x, a.y), (b.x, b.y))


def test_unknown_target_gives_no_route(navigator) -> None:
    assert navigator.route(parse_target("kpp"), parse_target("42-101")) is None


def test_route_to_non_numbered_building(navigator) -> None:
    route = navigator.route(parse_target("kpp"), parse_target("sport"))

    assert route is not None
    assert route.to_label == "спортзал"
    assert "Войдите в спортзал" in route.text()


def test_goes_from_6_to_7_through_the_tunnel_under_kpp(navigator) -> None:
    route = navigator.route(parse_target("6@1"), parse_target("7@1"))

    assert route is not None
    text = "\n".join(route.steps)
    assert "подземн" in text
    assert "Выйдите" not in text  # на улицу не выходим
    assert any(point.floor == -1 for point in route.points)  # под землёй - для 3D-линии ниже уровня земли


def test_prefers_warm_passages_and_offers_street_route_as_alternative(navigator) -> None:
    route = navigator.route(parse_target("2@2"), parse_target("7@1"))

    assert route is not None
    assert all(point.floor != 0 for point in route.points)  # ни шагу по улице
    assert route.alternative is not None
    assert any(point.floor == 0 for point in route.alternative.points)
    assert "По улице" in route.text()


def test_no_alternative_when_route_already_goes_outside(navigator) -> None:
    route = navigator.route(parse_target("kpp"), parse_target("7-404"))

    assert route is not None
    assert route.alternative is None
