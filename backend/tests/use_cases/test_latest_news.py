from src.domain.data import Data
from src.use_cases.latest_news import LatestNews


async def test_returns_newest_news_by_publication_date(fake_data_store_service) -> None:
    store = fake_data_store_service.store
    store[1] = Data(id=1, source="https://uust.ru/news/get/new", content="Новость УУНиТ от 29.09.2026: Новая")
    store[2] = Data(id=2, source="https://uust.ru/news/get/old", content="Новость УУНиТ от 01.09.2026: Старая")
    store[3] = Data(id=3, source="", content="Факт, не новость")

    news = await LatestNews(fake_data_store_service).execute(limit=5)

    assert [item.id for item in news] == [1, 2]
