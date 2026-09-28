from src.repositories.json_campus_repository import JsonCampusRepository
from src.services.campus_service import CampusService


def test_places_hint_lists_buildings_including_non_numbered_ones() -> None:
    hint = CampusService(JsonCampusRepository()).places_hint()

    assert "-> sport" in hint
    assert "-> kpp" in hint
    assert "-> 7" in hint
    assert "-> place:library" in hint
