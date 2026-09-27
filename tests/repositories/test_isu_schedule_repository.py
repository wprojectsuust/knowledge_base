import datetime as dt

from src.repositories.isu_schedule_repository import IsuScheduleRepository, _extract_venue, _week_number_for_date


def test_week_number_for_date_in_autumn_semester() -> None:
    # 1 сентября - понедельник первой недели, значит она же неделя 1
    assert _week_number_for_date(dt.date(2026, 9, 1)) == 1
    assert _week_number_for_date(dt.date(2026, 9, 8)) == 2


def test_week_number_for_date_in_january_uses_previous_september() -> None:
    week = _week_number_for_date(dt.date(2027, 1, 15))
    assert week >= 1


def test_extract_venue_finds_auditorium_pattern() -> None:
    assert _extract_venue("Матанализ (Иванов И.И.) ауд. 305") == "ауд. 305"


def test_extract_venue_returns_none_when_no_match() -> None:
    assert _extract_venue("Матанализ (Иванов И.И.)") is None


async def test_get_day_schedule_returns_none_for_unknown_group() -> None:
    repo = IsuScheduleRepository()

    result = await repo.get_day_schedule("НЕ-СУЩЕСТВУЮЩАЯ-ГРУППА", "2026-09-30")

    assert result is None
