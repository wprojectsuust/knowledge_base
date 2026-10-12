import json
from datetime import datetime, timezone

from src.domain.event import RawEvent
from src.use_cases.classify_events import ClassifyEvents


def _raw(n: int, title: str) -> RawEvent:
    return RawEvent(slug=f"e{n}", title=title, starts_at=datetime(2026, 10, n, tzinfo=timezone.utc), url=f"https://uust.ru/events/get/e{n}/")


async def test_labels_each_event_with_topic_format_and_online(fake_llm_service) -> None:
    fake_llm_service.response = json.dumps(
        [
            {"n": 1, "topic": "Карьера и бизнес", "format": "Консультация", "online": False},
            {"n": 2, "topic": "Спорт и здоровье", "format": "Соревнование и игра", "online": True},
        ],
        ensure_ascii=False,
    )

    events = await ClassifyEvents(fake_llm_service).execute([_raw(1, "Карьерные консультации"), _raw(2, "Онлайн-турнир по шахматам")])

    assert [(e.slug, e.topic, e.format, e.online) for e in events] == [
        ("e1", "Карьера и бизнес", "Консультация", False),
        ("e2", "Спорт и здоровье", "Соревнование и игра", True),
    ]
    assert "Карьерные консультации" in fake_llm_service.last_prompt
    assert "Стипендии и гранты" in fake_llm_service.last_prompt  # LLM видит допустимые значения


async def test_broken_llm_answer_still_imports_events_as_other(fake_llm_service) -> None:
    fake_llm_service.response = "не JSON"

    events = await ClassifyEvents(fake_llm_service).execute([_raw(1, "Что-то")])

    assert (events[0].topic, events[0].format) == ("Другое", "Другое")


async def test_one_llm_call_per_batch(fake_llm_service) -> None:
    fake_llm_service.response = "[]"

    await ClassifyEvents(fake_llm_service, batch_size=20).execute([_raw(n % 28 + 1, f"Событие {n}") for n in range(45)])

    assert fake_llm_service.call_count == 3
