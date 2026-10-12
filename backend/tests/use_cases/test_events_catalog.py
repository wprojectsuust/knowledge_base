import json
from datetime import datetime, timezone

from src.domain.event import Event, EventQuery, RawEvent
from src.services.events_service import EventsService
from src.services.llm_service import LLMUnavailableError
from src.use_cases.classify_events import ClassifyEvents
from src.use_cases.import_events import ImportEvents
from src.use_cases.list_events import ListEvents

WHEN = datetime(2026, 10, 17, 9, tzinfo=timezone.utc)


def _raw(slug: str) -> RawEvent:
    return RawEvent(slug=slug, title=f"Событие {slug}", starts_at=WHEN, url=f"https://uust.ru/events/get/{slug}/")


class FakeSource:
    def __init__(self, events) -> None:
        self.events = events

    async def latest(self, pages: int):
        return self.events


class FakeStore:
    def __init__(self) -> None:
        self.events: dict[str, Event] = {}

    async def known_slugs(self, slugs):
        return {slug for slug in slugs if slug in self.events}

    async def save_many(self, events):
        self.events.update({event.slug: event for event in events})

    async def find(self, query: EventQuery):
        return [e for e in self.events.values() if not query.topics or e.topic in query.topics][: query.limit]

    async def facets(self, query: EventQuery):
        counts: dict[str, dict[str, int]] = {"topic": {}, "format": {}}
        for e in self.events.values():
            counts["topic"][e.topic] = counts["topic"].get(e.topic, 0) + 1
            counts["format"][e.format] = counts["format"].get(e.format, 0) + 1
        return counts


async def test_imports_only_new_events_and_labels_them(fake_llm_service) -> None:
    store = FakeStore()
    store.events["old"] = Event(slug="old", title="Старое", starts_at=WHEN, url="u", image=None, topic="Другое", format="Другое")
    fake_llm_service.response = json.dumps([{"n": 1, "topic": "Карьера и бизнес", "format": "Консультация"}], ensure_ascii=False)

    report = await ImportEvents(EventsService(FakeSource([_raw("new"), _raw("old")]), store), ClassifyEvents(fake_llm_service)).execute(pages=1)

    assert (report.imported, report.skipped) == (1, 1)
    assert store.events["new"].topic == "Карьера и бизнес"
    assert "Событие old" not in fake_llm_service.last_prompt  # известные не размечаем повторно


async def test_nothing_new_means_no_llm_calls(fake_llm_service) -> None:
    store = FakeStore()
    await store.save_many([Event(slug="a", title="A", starts_at=WHEN, url="u", image=None, topic="Другое", format="Другое")])

    await ImportEvents(EventsService(FakeSource([_raw("a")]), store), ClassifyEvents(fake_llm_service)).execute(pages=1)

    assert fake_llm_service.call_count == 0


async def test_llm_outage_falls_back_to_keyword_labels_without_waiting_again() -> None:
    class DownLLM:
        def __init__(self) -> None:
            self.calls = 0

        async def generate(self, prompt):
            self.calls += 1
            raise LLMUnavailableError("503")

    llm = DownLLM()
    store = FakeStore()
    source = FakeSource([RawEvent(slug=f"s{n}", title="Турнир по шахматам", starts_at=WHEN, url="u") for n in range(25)])

    report = await ImportEvents(EventsService(source, store), ClassifyEvents(llm, batch_size=10)).execute(pages=3)

    assert report.imported == 25 and report.failed == 0
    assert store.events["s0"].topic == "Спорт и здоровье"  # разметка по ключевым словам
    assert llm.calls == 1  # после первого отказа LLM больше не ждём


async def test_list_returns_events_and_counts_for_every_topic() -> None:
    store = FakeStore()
    await store.save_many([Event(slug="a", title="A", starts_at=WHEN, url="u", image=None, topic="Спорт и здоровье", format="Конкурс")])

    page = await ListEvents(EventsService(FakeSource([]), store)).execute(EventQuery())

    assert [e.slug for e in page.events] == ["a"]
    assert page.topics["Спорт и здоровье"] == 1 and page.topics["Наука и технологии"] == 0
    assert page.formats["Конкурс"] == 1


