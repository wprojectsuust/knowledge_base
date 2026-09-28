import logging

from src.domain.campus import Route, parse_target
from src.services.campus_service import CampusService

logger = logging.getLogger(__name__)

DEFAULT_CAMPUS_ID = "ugatu"


class BuildRoute:
    """Строит маршрут по кампусу между двумя точками в нотации навигатора. Если откуда не
    сказано - от КПП. Текст маршрута собирается по шаблону из шагов пути, без LLM."""

    def __init__(self, campus_service: CampusService) -> None:
        self._campus_service = campus_service

    async def execute(self, source: str | None, target: str) -> Route | None:
        source_target = parse_target(source or "kpp")
        target_target = parse_target(target)
        if source_target is None or target_target is None:
            logger.info("BuildRoute: не разобрал точки %r -> %r", source, target)
            return None

        campus_id = self._campus_for(target_target.building) or self._campus_for(source_target.building) or DEFAULT_CAMPUS_ID
        navigator = self._campus_service.navigator(campus_id)
        route = navigator.route(source_target, target_target) if navigator else None
        logger.info("BuildRoute: %r -> %r в %s: %s", source, target, campus_id, "найден" if route else "не найден")
        return route

    def _campus_for(self, building_id: str | None) -> str | None:
        if building_id is None:
            return None
        for campus in self._campus_service.list():
            if campus.building(building_id) is not None:
                return campus.id
        return None
