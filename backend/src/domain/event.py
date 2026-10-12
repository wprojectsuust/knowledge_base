from dataclasses import dataclass
from datetime import date, datetime

# Справочники каталога мероприятий. На uust.ru у событий нет ни тематики, ни формата - их
# размечает LLM при импорте (ClassifyEvents) строго в эти значения, чтобы фильтры были стабильными.
TOPICS = (
    "Наука и технологии",
    "Карьера и бизнес",
    "Учёба и поступление",
    "Стипендии и гранты",
    "Творчество и культура",
    "Спорт и здоровье",
    "Общество и волонтёрство",
    "Международное",
    "Другое",
)
FORMATS = (
    "Мастер-класс",
    "Лекция и встреча",
    "Конкурс",
    "Фестиваль и праздник",
    "Конференция и форум",
    "Соревнование и игра",
    "Консультация",
    "Другое",
)


def _normalize(value: str | None, allowed: tuple[str, ...]) -> str:
    cleaned = (value or "").strip().lower()
    return next((item for item in allowed if item.lower() == cleaned), "Другое")


def normalize_topic(value: str | None) -> str:
    return _normalize(value, TOPICS)


def normalize_format(value: str | None) -> str:
    return _normalize(value, FORMATS)


@dataclass(frozen=True, kw_only=True)
class RawEvent:
    """Карточка события с uust.ru/events: то, что есть на сайте, - до разметки."""

    slug: str
    title: str
    starts_at: datetime
    url: str
    image: str | None = None


@dataclass(frozen=True, kw_only=True)
class Event:
    """Мероприятие в каталоге: карточка с сайта + тематика и формат от LLM."""

    slug: str
    title: str
    starts_at: datetime
    url: str
    image: str | None
    topic: str
    format: str
    online: bool = False


@dataclass(frozen=True, kw_only=True)
class EventQuery:
    """Фильтры каталога. Пустой кортеж/None - без ограничения. Даты - включительно, по Уфе."""

    date_from: date | None = None
    date_to: date | None = None
    topics: tuple[str, ...] = ()
    formats: tuple[str, ...] = ()
    online: bool | None = None
    text: str = ""
    newest_first: bool = False  # прошедшие удобнее листать от свежих к старым
    limit: int = 60
