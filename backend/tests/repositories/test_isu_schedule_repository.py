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
    cleaned, venue = _extract_venue("Матанализ (Иванов И.И.) ауд. 305")

    assert venue == "ауд. 305"
    assert "ауд. 305" not in cleaned


def test_extract_venue_returns_none_when_no_match() -> None:
    cleaned, venue = _extract_venue("Матанализ (Иванов И.И.)")

    assert venue is None
    assert cleaned == "Матанализ (Иванов И.И.)"


def test_extract_venue_formats_building_and_room_and_strips_duplicate() -> None:
    cleaned, venue = _extract_venue("Матанализ (Иванов И.И.) Корпус 7 - 404")

    assert venue == "кабинет 7-404"
    assert "Корпус 7 - 404" not in cleaned
    assert cleaned == "Матанализ (Иванов И.И.)"


async def test_get_day_schedule_returns_none_for_unknown_group() -> None:
    repo = IsuScheduleRepository()

    result = await repo.get_day_schedule("НЕ-СУЩЕСТВУЮЩАЯ-ГРУППА", "2026-09-30")

    assert result is None


async def test_resolve_group_ignores_case_and_separators() -> None:
    repo = IsuScheduleRepository()

    assert await repo.resolve_group("ТОП-106Б") == "ТОП-106Б"
    assert await repo.resolve_group("топ106б") == "ТОП-106Б"
    assert await repo.resolve_group("  топ 106 б ") == "ТОП-106Б"
    # латинские буквы-двойники кириллицы (частая опечатка при смешанной раскладке)
    assert await repo.resolve_group("TOП-106Б") == "ТОП-106Б"
    assert await repo.resolve_group("1-1.1.1.-26а") == "1-1.1.1.-26А"


async def test_resolve_group_returns_none_for_unknown_group() -> None:
    assert await IsuScheduleRepository().resolve_group("НЕ-СУЩЕСТВУЮЩАЯ-ГРУППА") is None


async def test_get_day_schedule_returns_none_when_isu_page_has_no_schedule(monkeypatch) -> None:
    # страница ошибки / сменили вёрстку - это «не удалось получить», а не «пар нет»
    repo = IsuScheduleRepository()

    async def fake_fetch(group_id: int, week: int) -> str:
        return "<html><body>Сервис временно недоступен</body></html>"

    monkeypatch.setattr(repo, "_fetch_html", fake_fetch)

    assert await repo.get_day_schedule("ТОП-106Б", "2026-09-30") is None
