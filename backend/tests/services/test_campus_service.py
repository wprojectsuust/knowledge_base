from src.repositories.json_campus_repository import JsonCampusRepository
from src.services.campus_service import CampusService


def test_places_hint_lists_buildings_including_non_numbered_ones() -> None:
    hint = CampusService(JsonCampusRepository()).places_hint()

    assert "-> sport" in hint
    assert "-> kpp" in hint
    assert "-> 7" in hint
    assert "-> place:library" in hint


def test_places_hint_skips_campuses_without_routes() -> None:
    # кампус БашГУ - заглушка без входов и графа: «как добраться до главного корпуса» не должно
    # превращаться в маршрут к «ф1», который потом не строится
    hint = CampusService(JsonCampusRepository()).places_hint()

    assert "ф1" not in hint
    assert "Корпус 7" in hint


def test_places_hint_marks_off_map_buildings_as_search_not_route() -> None:
    hint = CampusService(JsonCampusRepository()).places_hint()

    # «как добраться до главного корпуса» - это другой кампус (Заки Валиди, 32), не корпус 1
    assert "Главный корпус" in hint
    assert "Заки Валиди" in hint
    assert "search" in hint
