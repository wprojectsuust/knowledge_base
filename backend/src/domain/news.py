import re
from dataclasses import dataclass
from datetime import date

from src.domain.data import Data

# source у импортированных новостей (ImportNews) - ссылка на новость на uust.ru
NEWS_SOURCE_PREFIX = "https://uust.ru/news/get/"

# «какие есть мероприятия», «что нового», «будет ли концерт» - по смыслу новости почти не
# находятся (у каждой свои вопросы про конкретное событие), поэтому к ним подмешиваем свежие
_NEWS_QUESTION = re.compile(
    r"мероприят|событи|новост|нового|афиш|концерт|фестивал|конкурс|праздник|что (сейчас )?происходит|"
    r"куда сходить|чем заняться|анонс",
    re.IGNORECASE,
)
_NEWS_DATE = re.compile(r"Новость УУНиТ от (\d{2})\.(\d{2})\.(\d{4})")


def is_news_question(question: str) -> bool:
    return bool(_NEWS_QUESTION.search(question))


def newest_first(news: list[Data], limit: int) -> list[Data]:
    """Новости по дате публикации из текста («Новость УУНиТ от 28.09.2026: …»), новые первыми.
    id не годится: импорт идёт от новых к старым. Без даты - в конец."""

    def published(item: Data) -> date:
        match = _NEWS_DATE.search(item.content)
        return date(int(match[3]), int(match[2]), int(match[1])) if match else date.min

    return sorted(news, key=published, reverse=True)[:limit]


@dataclass(frozen=True, kw_only=True)
class NewsHeadline:
    """Новость из ленты сайта: ссылка (она же источник в базе знаний), заголовок, дата (ISO)."""

    url: str
    title: str
    published_at: str


@dataclass(frozen=True, kw_only=True)
class ImportReport:
    imported: int = 0
    skipped: int = 0  # уже были в базе знаний
    failed: int = 0  # не удалось скачать или проиндексировать
