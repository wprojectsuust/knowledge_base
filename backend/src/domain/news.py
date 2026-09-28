from dataclasses import dataclass


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
