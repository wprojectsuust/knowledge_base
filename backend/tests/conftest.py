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
        self.call_count = 0

    async def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        self.call_count += 1
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
    def __init__(self) -> None:
        self.call_count = 0

    async def encode(self, text: str) -> list[float]:
        self.call_count += 1
        return [float(len(text))]


@pytest.fixture
def fake_embedding_service() -> FakeEmbeddingService:
    return FakeEmbeddingService()


class FakeVectorSearchService:
    def __init__(self) -> None:
        self.index_calls: dict[int, list[float]] = {}
        self.divisions: dict[int, str | None] = {}
        self.scores: dict[int, float] = {}

    async def search(self, embedding: list[float], n_results: int = 6, division: str | None = None) -> list[int]:
        ids = list(self.index_calls.keys())
        if division:
            ids = [id_ for id_ in ids if self.divisions.get(id_) == division]
        return ids[:n_results]

    async def search_with_scores(
        self, embedding: list[float], n_results: int = 6, division: str | None = None
    ) -> list[tuple[int, float]]:
        ids = list(self.index_calls.keys())
        if division:
            ids = [id_ for id_ in ids if self.divisions.get(id_) == division]
        return [(id_, self.scores.get(id_, 1.0)) for id_ in ids][:n_results]

    async def index(self, id_: int, embedding: list[float], division: str | None = None) -> None:
        self.index_calls[id_] = embedding
        self.divisions[id_] = division

    async def remove(self, id_: int) -> None:
        self.index_calls.pop(id_, None)
        self.divisions.pop(id_, None)
        self.scores.pop(id_, None)


@pytest.fixture
def fake_vector_search_service() -> FakeVectorSearchService:
    return FakeVectorSearchService()


class FakeDataStoreService:
    def __init__(self) -> None:
        self.store: dict[int, Data] = {}
        self._next_id = 1

    async def get(self, id_: int) -> Data | None:
        return self.store.get(id_)

    async def get_many(self, ids: list[int]) -> list[Data]:
        return [self.store[id_] for id_ in ids if id_ in self.store]

    async def save(self, data: Data) -> int:
        new_id = self._next_id
        self._next_id += 1
        self.store[new_id] = Data(id=new_id, source=data.source, content=data.content, division=data.division)
        return new_id

    async def remove(self, id_: int) -> None:
        self.store.pop(id_, None)


@pytest.fixture
def fake_data_store_service() -> FakeDataStoreService:
    return FakeDataStoreService()


class FakeQuestionCacheService:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, question: str) -> str | None:
        return self.store.get(question)

    async def save(self, question: str, answer: str) -> None:
        self.store[question] = answer


@pytest.fixture
def fake_question_cache_service() -> FakeQuestionCacheService:
    return FakeQuestionCacheService()


class FakeScheduleService:
    def __init__(self) -> None:
        self.schedules: dict[tuple[str, str], object] = {}
        self.call_count = 0

    async def get_day_schedule(self, group: str, date: str):
        self.call_count += 1
        return self.schedules.get((group, date))


@pytest.fixture
def fake_schedule_service() -> FakeScheduleService:
    return FakeScheduleService()


class FakeScheduleCacheService:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str], object] = {}

    async def get(self, group: str, date: str):
        return self.store.get((group, date))

    async def save(self, day_schedule) -> None:
        self.store[(day_schedule.group, day_schedule.date)] = day_schedule


@pytest.fixture
def fake_schedule_cache_service() -> FakeScheduleCacheService:
    return FakeScheduleCacheService()


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
