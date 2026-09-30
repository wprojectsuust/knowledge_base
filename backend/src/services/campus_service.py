from __future__ import annotations

from src.domain.campus import Campus, CampusNavigator
from src.repositories.campus_repository import CampusRepository


class CampusService:
    """Прокси к CampusRepository. Граф маршрутов строится один раз на кампус (~0.3 с) и
    переиспользуется - данные статичные."""

    def __init__(self, repository: CampusRepository) -> None:
        self._repository = repository
        self._navigators: dict[str, CampusNavigator] = {}

    def list(self) -> list[Campus]:
        return self._repository.list()

    def navigator(self, campus_id: str) -> CampusNavigator | None:
        if campus_id not in self._navigators:
            campus = self._repository.get(campus_id)
            if campus is None:
                return None
            self._navigators[campus_id] = CampusNavigator(campus)
        return self._navigators[campus_id]

    def places_hint(self) -> str:
        """Справка для LLM: какие места есть на картах и как их называть в запросе маршрута."""
        lines = []
        for campus in self.list():
            if not campus.entrances:
                # кампус-заглушка без входов: маршрут не строится, но планировщик должен знать, что
                # «главный корпус» - это здесь, а не корпус 1 на карте, и искать ответ в базе знаний
                for building in campus.buildings:
                    lines.append(
                        f"- {building.name} ({campus.title}, {campus.address}) - не на карте, "
                        "маршрут не строится: это search, не route"
                    )
                continue
            for building in campus.buildings:
                name = f"Корпус {building.id}" if building.id.isdigit() else building.name
                lines.append(f"- {name} ({campus.title}) -> {building.id}")
            for place in campus.places:
                lines.append(f"- {place.label} (корпус {place.building}, {place.floor} этаж) -> place:{place.id}")
            for room in campus.rooms:
                lines.append(f"- {room.label} -> {room.building}-{room.number}")
            if any(place.kind == "cafe" for place in campus.places):
                lines.append("- Буфет/столовая, если не сказано какой -> place:cafe (ближайший)")
        return "\n".join(lines)
