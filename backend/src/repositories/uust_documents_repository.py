from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from src.domain.official_document import DOCUMENTS_PAGE_URL, OfficialDocument

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (UUST knowledge base documents importer)"}
_SKIPPED_SECTIONS = {"Последние опубликованные"}  # дублирует документы из остальных разделов


def _text(tag) -> str:
    return re.sub(r"\s+", " ", tag.get_text(" ", strip=True))


def parse_documents(html: str) -> list[OfficialDocument]:
    """Разделы-аккордеоны .composition__title, под каждым .composition__content со списками ссылок.
    Свёрнутые блоки скрыты только стилем (display: none) - в HTML они уже есть целиком.
    Подразделы - fieldset > legend; ссылки без текста (.sig - электронная подпись) пропускаем."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    documents: list[OfficialDocument] = []
    seen: set[str] = set()
    for title in soup.select(".composition__title"):
        section = _text(title)
        content = title.find_next_sibling(class_="composition__content")
        if content is None or section in _SKIPPED_SECTIONS:
            continue
        for link in content.find_all("a", href=True):
            name = _text(link)
            url = urljoin(DOCUMENTS_PAGE_URL, link["href"])
            if not name or url in seen:
                continue
            seen.add(url)
            fieldset = link.find_parent("fieldset")
            legend = fieldset.find("legend") if fieldset else None
            documents.append(
                OfficialDocument(title=name, url=url, section=section, group=_text(legend) if legend else "")
            )
    return documents


class UustDocumentsRepository:
    """OfficialDocumentsRepository поверх страницы uust.ru/sveden/document/ (httpx + BeautifulSoup)."""

    async def documents(self) -> list[OfficialDocument]:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=30.0, headers=_HEADERS, follow_redirects=True) as client:
                response = await client.get(DOCUMENTS_PAGE_URL)
        except httpx.HTTPError:
            logger.exception("UustDocuments: ошибка запроса %s", DOCUMENTS_PAGE_URL)
            return []
        if response.status_code != 200:
            logger.warning("UustDocuments: %s ответил %s", DOCUMENTS_PAGE_URL, response.status_code)
            return []
        return parse_documents(response.text)
