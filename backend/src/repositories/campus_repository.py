from __future__ import annotations

from typing import Protocol

from src.domain.campus import Campus


class CampusRepository(Protocol):
    """Источник данных о кампусах (корпуса, этажи, переходы, лестницы, входы...)."""

    def list(self) -> list[Campus]:
        ...

    def get(self, campus_id: str) -> Campus | None:
        ...
