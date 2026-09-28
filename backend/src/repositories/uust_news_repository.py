from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from src.domain.news import NewsHeadline

logger = logging.getLogger(__name__)

BASE_URL = "https://uust.ru"
_LIST_URL = f"{BASE_URL}/news/"
_PAGE_SIZE = 14  # столько карточек на одной странице ленты
_HEADERS = {"User-Agent": "Mozilla/5.0 (UUST knowledge base news importer)"}


def parse_news_list(html: str) -> list[NewsHeadline]:
    """Карточки ленты /news/: article.article-card со ссылкой, датой (time[datetime]) и заголовком."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    headlines = []
    for card in soup.select("article.article-card"):
        link = card.select_one("a.article-card__link[href]")
        title = card.select_one(".article-card__title")
        published = card.select_one("time[datetime]")
        if not link or not title or "/news/get/" not in link["href"]:
            continue
        headlines.append(
            NewsHeadline(
                url=urljoin(BASE_URL, link["href"]),
                title=title.get_text(" ", strip=True),
                published_at=published["datetime"] if published else "",
            )
        )
    return headlines


def parse_article_text(html: str) -> str | None:
    """Текст новости - div с классом ровно "article" (у шапки и исторических вставок есть
    модификаторы article--header / article--modal, их пропускаем)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    body = next((div for div in soup.find_all("div", class_="article") if div.get("class") == ["article"]), None)
    if body is None:
        return None
    for junk in body.find_all(["script", "style"]):
        junk.decompose()
    for br in body.find_all("br"):
        br.replace_with(" ")
    paragraphs = [re.sub(r"\s+", " ", p.get_text(" ", strip=True)) for p in body.find_all("p")]
    text = "\n".join(p for p in paragraphs if p) or re.sub(r"\s+", " ", body.get_text(" ", strip=True))
    return text or None


class UustNewsRepository:
    """NewsRepository поверх ленты новостей uust.ru (httpx + BeautifulSoup, без API - его нет)."""

    async def latest(self, limit: int) -> list[NewsHeadline]:
        headlines: list[NewsHeadline] = []
        page = 1
        while len(headlines) < limit:
            html = await self._get(_LIST_URL if page == 1 else f"{_LIST_URL}?page={page}")
            found = parse_news_list(html) if html else []
            if not found:
                break
            headlines.extend(item for item in found if item not in headlines)
            if len(found) < _PAGE_SIZE:
                break
            page += 1
        return headlines[:limit]

    async def article_text(self, url: str) -> str | None:
        html = await self._get(url)
        return parse_article_text(html) if html else None

    @staticmethod
    async def _get(url: str) -> str | None:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=20.0, headers=_HEADERS, follow_redirects=True) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.text
                logger.warning("UustNews: %s ответил %s", url, response.status_code)
        except httpx.HTTPError:
            logger.exception("UustNews: ошибка запроса %s", url)
        return None
