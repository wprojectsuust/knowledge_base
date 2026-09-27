import sys
import types
from typing import Callable
from unittest.mock import MagicMock

import pytest

from src.domain.data import Data


@pytest.fixture
def sample_data() -> Data:
    return Data(id=1, source="example.com", content="Деканат находится в корпусе 2")


class FakeLLMService:
    def __init__(self, response: str = "") -> None:
        self.response = response
        self.last_prompt: str | None = None

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response


@pytest.fixture
def make_fake_llm_service() -> Callable[[str], FakeLLMService]:
    def _factory(response: str = "") -> FakeLLMService:
        return FakeLLMService(response)

    return _factory


@pytest.fixture
def fake_llm_service(make_fake_llm_service: Callable[[str], FakeLLMService]) -> FakeLLMService:
    return make_fake_llm_service()


class FakeEmbeddingService:
    def encode(self, text: str) -> list[float]:
        return [float(len(text))]


@pytest.fixture
def fake_embedding_service() -> FakeEmbeddingService:
    return FakeEmbeddingService()


class FakeVectorSearchService:
    def __init__(self) -> None:
        self.index_calls: dict[int, list[float]] = {}

    def search(self, embedding: list[float], n_results: int = 6) -> list[int]:
        return list(self.index_calls.keys())[:n_results]

    def index(self, id_: int, embedding: list[float]) -> None:
        self.index_calls[id_] = embedding

    def remove(self, id_: int) -> None:
        self.index_calls.pop(id_, None)


@pytest.fixture
def fake_vector_search_service() -> FakeVectorSearchService:
    return FakeVectorSearchService()


class FakeDataStoreService:
    def __init__(self) -> None:
        self.store: dict[int, Data] = {}

    async def get(self, id_: int) -> Data | None:
        return self.store.get(id_)

    async def get_many(self, ids: list[int]) -> list[Data]:
        return [self.store[id_] for id_ in ids if id_ in self.store]

    async def save(self, data: Data) -> None:
        self.store[data.id] = data

    async def remove(self, id_: int) -> None:
        self.store.pop(id_, None)


@pytest.fixture
def fake_data_store_service() -> FakeDataStoreService:
    return FakeDataStoreService()


@pytest.fixture
def fake_chromadb(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Подменяет модуль chromadb в sys.modules, чтобы ChromaVectorRepository можно было
    протестировать без реальной библиотеки. Возвращает мок коллекции."""
    fake_collection = MagicMock()
    fake_client = MagicMock()
    fake_client.get_or_create_collection.return_value = fake_collection

    fake_module = types.ModuleType("chromadb")
    fake_module.PersistentClient = MagicMock(return_value=fake_client)
    monkeypatch.setitem(sys.modules, "chromadb", fake_module)

    return fake_collection


@pytest.fixture
def fake_asyncpg_pool(monkeypatch: pytest.MonkeyPatch):
    """Подменяет asyncpg в sys.modules, чтобы PostgresDataRepository можно было
    протестировать без реальной библиотеки/базы. Возвращает мок пула (AsyncMock)."""
    from unittest.mock import AsyncMock

    fake_pool = AsyncMock()

    async def _fake_create_pool(dsn, *args, **kwargs):
        return fake_pool

    fake_module = types.ModuleType("asyncpg")
    fake_module.create_pool = _fake_create_pool
    monkeypatch.setitem(sys.modules, "asyncpg", fake_module)

    return fake_pool


@pytest.fixture
def fake_openai(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Подменяет openai/httpx в sys.modules, чтобы GeminiProvider можно было
    протестировать без реальной библиотеки. Возвращает мок chat.completions.create."""
    fake_create = MagicMock()
    fake_client_instance = MagicMock()
    fake_client_instance.chat.completions.create = fake_create

    fake_openai_module = types.ModuleType("openai")
    fake_openai_module.OpenAI = MagicMock(return_value=fake_client_instance)
    monkeypatch.setitem(sys.modules, "openai", fake_openai_module)

    fake_httpx_module = types.ModuleType("httpx")
    fake_httpx_module.Client = MagicMock()
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx_module)

    return fake_create


@pytest.fixture
def fake_sentence_transformers(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Подменяет sentence_transformers в sys.modules, чтобы RubertTiny2Provider можно было
    протестировать без реальной библиотеки/скачивания модели. Возвращает мок модели."""
    fake_model = MagicMock()

    fake_module = types.ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = MagicMock(return_value=fake_model)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    return fake_model
