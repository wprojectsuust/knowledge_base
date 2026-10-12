from datetime import date, datetime, timezone

from src.domain.event import Event, EventQuery
from src.domain.plan import EventsTask
from src.use_cases.find_events import FindEvents


def _event(slug: str, day: int, title: str = "Событие") -> Event:
    return Event(slug=slug, title=title, starts_at=datetime(2026, 10, day, 6, tzinfo=timezone.utc),
                 url=f"https://uust.ru/events/get/{slug}/", image=None, topic="Наука и технологии", format="Конкурс")


class FakeEvents:
    def __init__(self, upcoming, past) -> None:
        self.upcoming, self.past = upcoming, past
        self.queries: list[EventQuery] = []

    async def find(self, query: EventQuery):
        self.queries.append(query)
        return self.past if query.newest_first else self.upcoming


TODAY = date(2026, 10, 12)


async def test_explicit_dates_and_filters_go_to_the_catalog_as_is() -> None:
    events = FakeEvents([_event("a", 20)], [])
    task = EventsTask(question="хакатоны в октябре", keywords=("хакатон",), date_from=date(2026, 10, 1),
                      date_to=date(2026, 10, 31), topic="Наука и технологии")

    found = await FindEvents(events, today=lambda: TODAY).execute(task)

    query = events.queries[0]
    assert (query.date_from, query.date_to) == (date(2026, 10, 1), date(2026, 10, 31))
    assert query.keywords == ("хакатон",)
    assert query.topics == ()  # со словами тематику не фильтруем - разметка могла разойтись
    assert [e.slug for e in found.events] == ["a"]


async def test_without_dates_upcoming_first_then_recent_past_when_few() -> None:
    events = FakeEvents([_event("next", 20)], [_event("prev", 5)])

    found = await FindEvents(events, today=lambda: TODAY).execute(EventsTask(question="какие есть олимпиады", keywords=("олимпиад",)))

    assert events.queries[0].date_from == TODAY and not events.queries[0].newest_first
    assert events.queries[1].date_to == date(2026, 10, 11) and events.queries[1].newest_first
    assert [e.slug for e in found.events] == ["next", "prev"]


async def test_keywords_found_nothing_retries_by_dates_and_topic_only() -> None:
    class KeywordMiss(FakeEvents):
        async def find(self, query):
            self.queries.append(query)
            return [] if query.keywords else [_event("any", 20)]

    events = KeywordMiss([], [])

    found = await FindEvents(events, today=lambda: TODAY).execute(EventsTask(question="что на неделе", keywords=("квиз",),
                                                                       date_from=TODAY, date_to=date(2026, 10, 18)))

    assert [e.slug for e in found.events] == ["any"]
    assert found.relaxed  # честно скажем, что по словам ничего не нашлось


async def test_context_lists_events_with_dates_and_links() -> None:
    events = FakeEvents([_event("a", 20, "Хакатон «Код УУНиТ»")], [])

    found = await FindEvents(events, today=lambda: TODAY).execute(EventsTask(question="хакатоны"))

    text = found.as_context().content
    assert "Хакатон «Код УУНиТ»" in text and "20.10.2026" in text and "https://uust.ru/events/get/a/" in text


async def test_topic_filters_only_when_there_are_no_keywords() -> None:
    events = FakeEvents([_event("a", 20)] * 3, [])

    await FindEvents(events, today=lambda: TODAY).execute(EventsTask(question="что по науке", topic="Наука и технологии"))

    assert events.queries[0].topics == ("Наука и технологии",)
