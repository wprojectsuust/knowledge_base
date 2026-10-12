from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.repositories.uust_events_repository import parse_events_page

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_parses_event_cards_with_date_image_and_absolute_links() -> None:
    events = parse_events_page((FIXTURES / "uust_events.html").read_text(encoding="utf-8"))

    assert len(events) == 3  # карточка без даты пропущена
    first = events[0]
    assert first.slug == "razbor-slozhnyh-zadanij-ege-besplatnye-master-klassy-po-obshestvoznaniyu-i-fizike-v-uunit"
    assert first.title.startswith("Разбор сложных заданий ЕГЭ")
    assert first.url == f"https://uust.ru/events/get/{first.slug}/"
    assert first.starts_at == datetime(2026, 10, 17, 9, 0, tzinfo=timezone(timedelta(hours=5)))
    assert first.image.startswith("https://uust.ru/media/press-center/events/covers/")
