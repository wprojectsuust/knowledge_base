from src.domain.data import Data
from src.use_cases.latest_news import LatestNews


async def test_returns_newest_news_by_publication_date(fake_data_store_service) -> None:
    store = fake_data_store_service.store
    store[1] = Data(id=1, source="https://uust.ru/news/get/new", content="Новость УУНиТ от 29.09.2026: Новая")
    store[2] = Data(id=2, source="https://uust.ru/news/get/old", content="Новость УУНиТ от 01.09.2026: Старая")
    store[3] = Data(id=3, source="", content="Факт, не новость")

    news = await LatestNews(fake_data_store_service).execute(limit=5)

    assert [item.id for item in news] == [1, 2]


async def test_upcoming_events_from_catalog_come_first(fake_data_store_service) -> None:
    from datetime import datetime, timezone

    from src.domain.event import Event

    class FakeEvents:
        def __init__(self) -> None:
            self.query = None

        async def find(self, query):
            self.query = query
            return [Event(slug="it", title="ИТ-фестиваль", starts_at=datetime(2026, 10, 20, 6, tzinfo=timezone.utc),
                          url="https://uust.ru/events/get/it/", image=None, topic="Наука и технологии",
                          format="Фестиваль и праздник")]

    events = FakeEvents()
    fake_data_store_service.store[1] = Data(id=1, source="https://uust.ru/news/get/n", content="Новость УУНиТ от 29.09.2026: Н")

    found = await LatestNews(fake_data_store_service, events_service=events).execute(limit=5)

    digest = found[0]
    assert "Ближайшие мероприятия" in digest.content
    assert "20.10" in digest.content and "ИТ-фестиваль" in digest.content and "https://uust.ru/events/get/it/" in digest.content
    assert events.query.date_from is not None  # только предстоящие
    assert found[1].id == 1
