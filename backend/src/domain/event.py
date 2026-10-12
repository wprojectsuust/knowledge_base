import re
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


# Запасная разметка по ключевым словам названия - если LLM недоступна или медленная, каталог
# всё равно пополняется. Порядок важен: первое совпадение побеждает («конкурс на стипендию» -
# это стипендии, а не просто конкурс).
_TOPIC_RULES = (
    ("Стипендии и гранты", r"стипенд|грант|премии?\b|материальн"),
    ("Учёба и поступление", r"егэ|олимпиад|абитуриент|поступлен|приёмн|приемн|школьник|экзамен|сесси"),
    ("Карьера и бизнес", r"карьер|ваканс|стажир|работодател|предприним|бизнес|трудоустр"),
    ("Наука и технологии", r"конференц|наук|исследова|лаборатор|техно|инженер|программир|хакатон|it\b|ит-"),
    ("Международное", r"международн|иностран|зарубеж"),
    ("Спорт и здоровье", r"спорт|турнир|соревнован|чемпионат|забег|шахмат|футбол|волейбол|здоров|гто"),
    ("Творчество и культура", r"концерт|фестивал|праздни|театр|выставк|творч|музык|танц|кино|литератур"),
    ("Общество и волонтёрство", r"волонт|донор|акци|эколог|субботник|памят|патриот|благотвор"),
)
_FORMAT_RULES = (
    ("Мастер-класс", r"мастер-класс|тренинг|практикум|воркшоп|разбер|пробн"),
    ("Консультация", r"консультац"),
    ("Конференция и форум", r"конференц|форум|школа|симпозиум|слёт|слет"),
    ("Соревнование и игра", r"турнир|соревнован|чемпионат|игра|квиз|квест|хакатон"),
    ("Конкурс", r"конкурс|олимпиад|премия|отбор"),
    ("Фестиваль и праздник", r"фестивал|праздни|концерт|день\s"),
    ("Лекция и встреча", r"лекци|встреч|семинар|вебинар|беседа|круглый стол|открыт"),
)
_ONLINE = re.compile(r"онлайн|вебинар|дистанцион|online", re.IGNORECASE)


def guess_labels(title: str) -> tuple[str, str, bool]:
    """Тематика, формат и «онлайн» по словам названия - запасной вариант к разметке LLM."""
    lowered = title.lower()
    topic = next((name for name, pattern in _TOPIC_RULES if re.search(pattern, lowered)), "Другое")
    fmt = next((name for name, pattern in _FORMAT_RULES if re.search(pattern, lowered)), "Другое")
    return topic, fmt, bool(_ONLINE.search(title))


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
    # любое из слов в названии (для консультанта: «хакатон», «олимпиад») - в отличие от text,
    # где ищется вся строка целиком (поиск на странице каталога)
    keywords: tuple[str, ...] = ()
    newest_first: bool = False  # прошедшие удобнее листать от свежих к старым
    limit: int = 60
