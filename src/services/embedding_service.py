from __future__ import annotations

import asyncio
import logging
from typing import Protocol

from src.logging_utils import preview

logger = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    """Абстракция над конкретной моделью эмбеддингов."""

    def encode(self, text: str) -> list[float]:
        ...


class RubertTiny2Provider:
    """Провайдер поверх cointegrated/rubert-tiny2, считается на CPU."""

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        logger.info("Загружаю модель эмбеддингов cointegrated/rubert-tiny2 (CPU)...")
        self._model = SentenceTransformer("cointegrated/rubert-tiny2", device="cpu")
        logger.info("Модель эмбеддингов загружена")

    def encode(self, text: str) -> list[float]:
        logger.debug("Embedding encode: %s", preview(text, 100))
        return self._model.encode(text, normalize_embeddings=True).tolist()


class EmbeddingService:
    """Обёртка над EmbeddingProvider - позволяет быстро сменить модель эмбеддингов.

    encode() асинхронный: инференс sentence-transformers - CPU-bound синхронная работа,
    без to_thread она блокировала бы event loop на время расчёта эмбеддинга."""

    def __init__(self, provider: EmbeddingProvider) -> None:
        self._provider = provider

    async def encode(self, text: str) -> list[float]:
        return await asyncio.to_thread(self._provider.encode, text)

    @classmethod
    def from_env(cls) -> "EmbeddingService":
        return cls(RubertTiny2Provider())
