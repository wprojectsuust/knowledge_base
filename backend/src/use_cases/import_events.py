import logging
from dataclasses import dataclass

from src.services.events_service import EventsService
from src.services.llm_service import LLMUnavailableError
from src.use_cases.classify_events import ClassifyEvents

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class EventsImportReport:
    imported: int = 0
    skipped: int = 0  # уже в каталоге
    failed: int = 0


class ImportEvents:
    """Пополняет каталог мероприятий с uust.ru/events: новые события размечаются LLM (тематика,
    формат) и сохраняются пачками; уже известные пропускаются без вызовов LLM. LLM недоступна -
    остальные пачки доберём в следующий прогон."""

    def __init__(self, events_service: EventsService, classify_events: ClassifyEvents) -> None:
        self._events_service = events_service
        self._classify_events = classify_events

    async def execute(self, pages: int) -> EventsImportReport:
        found = await self._events_service.latest_from_site(pages)
        known = await self._events_service.known_slugs([event.slug for event in found])
        fresh = [event for event in found if event.slug not in known]
        imported = 0
        # размечаем и сохраняем пачками: медленная или упавшая LLM не теряет уже размеченное
        for start in range(0, len(fresh), self._classify_events.batch_size):
            batch = fresh[start : start + self._classify_events.batch_size]
            try:
                events = await self._classify_events.execute(batch)
            except LLMUnavailableError:
                logger.warning("ImportEvents: LLM недоступна, %d событий - в следующий раз", len(fresh) - imported)
                break
            await self._events_service.save_many(events)
            imported += len(events)
        report = EventsImportReport(imported=imported, skipped=len(known), failed=len(fresh) - imported)
        logger.info("ImportEvents: %s", report)
        return report
