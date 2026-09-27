from __future__ import annotations

from typing import Protocol


class EmbeddingProvider(Protocol):
    """Абстракция над конкретной моделью эмбеддингов."""

    def encode(self, text: str) -> list[float]:
        ...


class RubertTiny2Provider:
    """Провайдер поверх cointegrated/rubert-tiny2, считается на CPU."""

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer("cointegrated/rubert-tiny2", device="cpu")

    def encode(self, text: str) -> list[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()


class EmbeddingService:
    """Обёртка над EmbeddingProvider - позволяет быстро сменить модель эмбеддингов."""

    def __init__(self, provider: EmbeddingProvider) -> None:
        self._provider = provider

    def encode(self, text: str) -> list[float]:
        return self._provider.encode(text)

    @classmethod
    def from_env(cls) -> "EmbeddingService":
        return cls(RubertTiny2Provider())
