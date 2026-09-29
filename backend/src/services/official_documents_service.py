from __future__ import annotations

from src.domain.official_document import OfficialDocument
from src.repositories.official_documents_repository import OfficialDocumentsRepository


class OfficialDocumentsService:
    """Прокси к OfficialDocumentsRepository - изолирует юз-кейсы от конкретного источника."""

    def __init__(self, repository: OfficialDocumentsRepository) -> None:
        self._repository = repository

    async def documents(self) -> list[OfficialDocument]:
        return await self._repository.documents()
