import asyncio
import time
from unittest.mock import MagicMock

import src.config as config
from src.services.embedding_service import EmbeddingService, RubertTiny2Provider


async def test_embedding_service_delegates_to_provider() -> None:
    class FakeEmbeddingProvider:
        def encode(self, text: str) -> list[float]:
            return [float(len(text)), 0.0, 1.0]

    service = EmbeddingService(FakeEmbeddingProvider())

    vector = await service.encode("Где деканат?")

    assert vector == [12.0, 0.0, 1.0]


async def test_embedding_service_limits_concurrent_calls(monkeypatch) -> None:
    monkeypatch.setattr(config, "EMBEDDING_MAX_CONCURRENCY", 2)

    active = 0
    max_active = 0

    class SlowEmbeddingProvider:
        def encode(self, text: str) -> list[float]:
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            time.sleep(0.05)
            active -= 1
            return [0.0]

    service = EmbeddingService(SlowEmbeddingProvider())

    await asyncio.gather(*(service.encode("x") for _ in range(6)))

    assert max_active <= 2


def test_rubert_provider_encode_normalizes_and_returns_list(fake_sentence_transformers: MagicMock) -> None:
    fake_sentence_transformers.encode.return_value.tolist.return_value = [0.1, 0.2]

    provider = RubertTiny2Provider()
    result = provider.encode("привет")

    assert result == [0.1, 0.2]
    fake_sentence_transformers.encode.assert_called_once_with("привет", normalize_embeddings=True)
