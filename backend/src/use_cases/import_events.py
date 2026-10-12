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
    формат) и сохраняются; уже известные пропускаются без вызовов LLM. LLM недоступна - новые
    события не сохраняем, доберём в следующий прогон."""

    def __init__(self, events_service: EventsService, classify_events: ClassifyEvents) -> None:
        self._events_service = events_service
        self._classify_events = classify_events

    async def execute(self, pages: int) -> EventsImportReport:
        found = await self._events_service.latest_from_site(pages)
        known = await self._events_service.known_slugs([event.slug for event in found])
        fresh = [event for event in found if event.slug not in known]
        if not fresh:
            report = EventsImportReport(skipped=len(known))
        else:
            try:
                events = await self._classify_events.execute(fresh)
            except LLMUnavailableError:
                logger.warning("ImportEvents: LLM недоступна, %d новых событий - в следующий раз", len(fresh))
                return EventsImportReport(skipped=len(known), failed=len(fresh))
            await self._events_service.save_many(events)
            report = EventsImportReport(imported=len(events), skipped=len(known))
        logger.info("ImportEvents: %s", report)
        return report
