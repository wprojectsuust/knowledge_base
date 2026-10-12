from __future__ import annotations

import logging
from datetime import datetime
from urllib.parse import urljoin

from src.domain.event import RawEvent

logger = logging.getLogger(__name__)

BASE_URL = "https://uust.ru"
_LIST_URL = f"{BASE_URL}/events/"
_HEADERS = {"User-Agent": "Mozilla/5.0 (UUST events catalog importer)"}


def parse_events_page(html: str) -> list[RawEvent]:
    """Карточки a.event на uust.ru/events: ссылка /events/get/<slug>, time[datetime], обложка,
    заголовок .event__title. Карточки без даты пропускаем - в каталоге без даты они бесполезны."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    events = []
    for card in soup.select("a.event[href]"):
        href = card["href"]
        title = card.select_one(".event__title")
        when = card.select_one("time[datetime]")
        if "/events/get/" not in href or title is None or when is None:
            continue
        slug = href.split("/events/get/", 1)[1].strip("/")
        try:
            starts_at = datetime.fromisoformat(when["datetime"])
        except ValueError:
            continue
        image = card.select_one("img[src]")
        events.append(
            RawEvent(
                slug=slug,
                title=" ".join(title.get_text(" ", strip=True).split()),
                starts_at=starts_at,
                url=f"{BASE_URL}/events/get/{slug}/",
                image=urljoin(BASE_URL, image["src"]) if image else None,
            )
        )
    return events


class UustEventsRepository:
    """Источник событий - страницы uust.ru/events/?page=N (API у сайта нет)."""

    async def latest(self, pages: int) -> list[RawEvent]:
        import httpx

        events: list[RawEvent] = []
        seen: set[str] = set()
        async with httpx.AsyncClient(timeout=25.0, headers=_HEADERS, follow_redirects=True) as client:
            for page in range(1, pages + 1):
                try:
                    response = await client.get(_LIST_URL, params={"page": page} if page > 1 else None)
                except httpx.HTTPError:
                    logger.exception("UustEvents: ошибка запроса страницы %d", page)
                    break
                found = parse_events_page(response.text) if response.status_code == 200 else []
                fresh = [event for event in found if event.slug not in seen]
                if not fresh:
                    break  # страницы кончились (сайт отдаёт последнюю или пустую)
                seen.update(event.slug for event in fresh)
                events.extend(fresh)
        logger.info("UustEvents: %d событий с %d страниц", len(events), pages)
        return events
