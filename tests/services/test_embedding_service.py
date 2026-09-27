from unittest.mock import MagicMock

from src.services.embedding_service import EmbeddingService, RubertTiny2Provider


def test_embedding_service_delegates_to_provider() -> None:
    class FakeEmbeddingProvider:
        def encode(self, text: str) -> list[float]:
            return [float(len(text)), 0.0, 1.0]

    service = EmbeddingService(FakeEmbeddingProvider())

    vector = service.encode("Где деканат?")

    assert vector == [12.0, 0.0, 1.0]


def test_rubert_provider_encode_normalizes_and_returns_list(fake_sentence_transformers: MagicMock) -> None:
    fake_sentence_transformers.encode.return_value.tolist.return_value = [0.1, 0.2]

    provider = RubertTiny2Provider()
    result = provider.encode("привет")

    assert result == [0.1, 0.2]
    fake_sentence_transformers.encode.assert_called_once_with("привет", normalize_embeddings=True)
