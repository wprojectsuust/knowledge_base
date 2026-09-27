from src.services.embedding_service import EmbeddingService


class FakeEmbeddingProvider:
    def encode(self, text: str) -> list[float]:
        return [float(len(text)), 0.0, 1.0]


def test_embedding_service_delegates_to_provider() -> None:
    service = EmbeddingService(FakeEmbeddingProvider())

    vector = service.encode("Где деканат?")

    assert vector == [12.0, 0.0, 1.0]
