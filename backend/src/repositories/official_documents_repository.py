from __future__ import annotations

from typing import Protocol

from src.domain.official_document import OfficialDocument


class OfficialDocumentsRepository(Protocol):
    """Источник списка официальных документов вуза (страница «Документы» uust.ru)."""

    async def documents(self) -> list[OfficialDocument]:
        """Все документы со страницы; пустой список, если её не удалось скачать или разобрать."""
        ...
