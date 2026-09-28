import pytest

from src.domain.data import Data
from src.domain.news import NewsHeadline
from src.use_cases.analyze_data import AnalyzeDataByLLMForNewData
from src.use_cases.import_news import ImportNews
from src.use_cases.new_data import NewData

OLD = NewsHeadline(url="https://uust.ru/news/get/old", title="Старая новость", published_at="2026-09-20T10:00:00+05:00")
FRESH = NewsHeadline(
    url="https://uust.ru/news/get/fresh", title="ИТ-фестиваль ТОП-ИТ", published_at="2026-09-25T09:45:00+05:00"
)
BROKEN = NewsHeadline(url="https://uust.ru/news/get/broken", title="Битая", published_at="2026-09-26T09:00:00+05:00")


class FakeNewsService:
    def __init__(self, headlines, texts) -> None:
        self.headlines = headlines
        self.texts = texts
        self.fetched: list[str] = []

    async def latest(self, limit: int) -> list[NewsHeadline]:
        return self.headlines[:limit]

    async def article_text(self, url: str) -> str | None:
        self.fetched.append(url)
        return self.texts.get(url)


@pytest.fixture
def make_import(fake_llm_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service):
    def _make(news_service) -> ImportNews:
        fake_llm_service.response = '["какие мероприятия в УУНиТ"]'
        new_data = NewData(
            AnalyzeDataByLLMForNewData(fake_llm_service),
            fake_embedding_service,
            fake_vector_search_service,
            fake_data_store_service,
        )
        return ImportNews(news_service, fake_data_store_service, new_data)

    return _make


async def test_imports_only_news_not_seen_before(make_import, fake_data_store_service) -> None:
    fake_data_store_service.store[1] = Data(id=1, source=OLD.url, content="уже загружена")
    fake_data_store_service._next_id = 2
    news = FakeNewsService([FRESH, OLD], {FRESH.url: "Открылся фестиваль.", OLD.url: "..."})

    report = await make_import(news).execute(limit=10)

    assert report.imported == 1
    assert report.skipped == 1
    assert news.fetched == [FRESH.url]  # уже загруженную даже не скачиваем
    saved = fake_data_store_service.store[2]
    assert saved.source == FRESH.url
    # дата и заголовок - в самом тексте: без них LLM не отличит старое мероприятие от будущего
    assert saved.content.startswith("Новость УУНиТ от 25.09.2026: ИТ-фестиваль ТОП-ИТ")
    assert "Открылся фестиваль." in saved.content


async def test_counts_news_without_body_as_failed_and_continues(make_import, fake_data_store_service) -> None:
    news = FakeNewsService([BROKEN, FRESH], {FRESH.url: "Открылся фестиваль."})

    report = await make_import(news).execute(limit=10)

    assert report.failed == 1
    assert report.imported == 1
