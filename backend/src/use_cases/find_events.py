import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta

from src import config
from src.domain.data import Data
from src.domain.event import Event, EventQuery
from src.domain.plan import EventsTask
from src.services.events_service import EventsService

logger = logging.getLogger(__name__)

_LIMIT = 10
_ENOUGH_UPCOMING = 3  # меньше - добавим недавно прошедшие, иначе ответ «ничего нет» вводит в заблуждение
_RECENT = 5
EVENTS_CONTEXT_ID = -2  # отрицательный - не пересечётся с id фрагментов базы знаний


@dataclass(frozen=True, kw_only=True)
class FoundEvents:
    events: list[Event]
    relaxed: bool = False  # по словам ничего не нашлось - показаны события за даты/тематику без них

    def as_context(self) -> Data:
        """Найденное - одним фрагментом для LLM: даты по Уфе и ссылки на страницы мероприятий."""
        today = datetime.now(config.LOCAL_TZ).date()
        lines = []
        for event in self.events:
            local = event.starts_at.astimezone(config.LOCAL_TZ)
            when = "прошло" if local.date() < today else "предстоит"
            online = ", онлайн" if event.online else ""
            lines.append(f"- {event_when(local)} ({when}) - {event.title} ({event.topic}, {event.format}{online}): {event.url}")
        note = (
            "По ключевым словам вопроса мероприятий не нашлось, ниже - другие мероприятия за эти даты.\n"
            if self.relaxed
            else ""
        )
        body = "\n".join(lines) if lines else "Подходящих мероприятий в каталоге нет."
        return Data(
            id=EVENTS_CONTEXT_ID,
            source="https://uust.ru/events/",
            content=f"Каталог мероприятий УУНиТ (вкладка «Мероприятия»), сегодня {today:%d.%m.%Y}:\n{note}{body}",
        )


def event_when(local: datetime) -> str:
    """Дата и время начала. «Неровное» время (16:43) на uust.ru - это время публикации карточки, а
    не начала события: его не показываем, чтобы не вводить в заблуждение."""
    return f"{local:%d.%m.%Y %H:%M}" if local.minute % 15 == 0 else f"{local:%d.%m.%Y}"


class FindEvents:
    """Ищет мероприятия для ответа консультанта - в каталоге (таблица events), а не в векторной базе:
    там точные даты, тематики и прошедшие события.

    Без дат - сначала предстоящие; если их мало, добавляются недавно прошедшие. Ключевые слова не
    нашли ничего - повторяем только по датам и тематике и честно помечаем это в контексте."""

    def __init__(self, events_service: EventsService, today: Callable[[], date] | None = None) -> None:
        self._events_service = events_service
        self._today = today or (lambda: datetime.now(config.LOCAL_TZ).date())

    async def execute(self, task: EventsTask) -> FoundEvents:
        found = await self._search(task)
        relaxed = False
        if not found and task.keywords:
            found = await self._search(replace(task, keywords=()))
            relaxed = bool(found)
        logger.info("FindEvents: %s -> %d мероприятий (relaxed=%s)", task, len(found), relaxed)
        return FoundEvents(events=found, relaxed=relaxed)

    async def _search(self, task: EventsTask) -> list[Event]:
        # слова названия точнее тематики: разметка каталога и догадка планировщика могут разойтись
        # («Я - профессионал»: каталог - учёба, планировщик - карьера), поэтому тематика - только без слов
        topics = (task.topic,) if task.topic and not task.keywords else ()
        base = EventQuery(keywords=task.keywords, topics=topics, limit=_LIMIT)
        if task.date_from or task.date_to:
            return await self._events_service.find(replace(base, date_from=task.date_from, date_to=task.date_to))
        today = self._today()
        upcoming = await self._events_service.find(replace(base, date_from=today))
        if len(upcoming) >= _ENOUGH_UPCOMING:
            return upcoming
        past = await self._events_service.find(
            replace(base, date_to=today - timedelta(days=1), newest_first=True, limit=_RECENT)
        )
        return upcoming + past
