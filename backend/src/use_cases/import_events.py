import logging
from dataclasses import dataclass

from src.services.events_service import EventsService
from src.use_cases.classify_events import ClassifyEvents

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class EventsImportReport:
    imported: int = 0
    skipped: int = 0  # уже в каталоге
    failed: int = 0


class ImportEvents:
    """Пополняет каталог мероприятий с uust.ru/events: новые события размечаются LLM (тематика,
    формат) и сохраняются пачками; уже известные пропускаются без вызовов LLM. Если LLM
    недоступна, ClassifyEvents размечает по ключевым словам - каталог пополняется всегда."""

    def __init__(self, events_service: EventsService, classify_events: ClassifyEvents) -> None:
        self._events_service = events_service
        self._classify_events = classify_events

    async def execute(self, pages: int) -> EventsImportReport:
        found = await self._events_service.latest_from_site(pages)
        known = await self._events_service.known_slugs([event.slug for event in found])
        fresh = [event for event in found if event.slug not in known]
        imported = 0
        # размечаем и сохраняем пачками: сбой посередине не теряет уже размеченное
        for start in range(0, len(fresh), self._classify_events.batch_size):
            batch = fresh[start : start + self._classify_events.batch_size]
            events = await self._classify_events.execute(batch)
            await self._events_service.save_many(events)
            imported += len(events)
        report = EventsImportReport(imported=imported, skipped=len(known), failed=len(fresh) - imported)
        logger.info("ImportEvents: %s", report)
        return report
