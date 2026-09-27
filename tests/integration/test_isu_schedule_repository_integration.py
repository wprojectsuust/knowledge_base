"""Интеграционный тест: реальный (недокументированный) эндпоинт ИСУ УУНиТ, никаких моков.

Зависит от того, что сайт ИСУ доступен и не поменял разметку - неизбежная хрупкость
живого скрейпинга стороннего сайта. По умолчанию pytest эти тесты пропускает
(см. addopts в pyproject.toml) - запуск явный: `pytest -m integration`.
"""

import datetime as dt

import pytest

from src.repositories.isu_schedule_repository import IsuScheduleRepository, _load_groups

pytestmark = pytest.mark.integration


async def test_fetches_some_schedule_for_a_real_group() -> None:
    groups = _load_groups()
    any_group = next(iter(groups))
    repo = IsuScheduleRepository()
    target_date = dt.date.today().isoformat()

    result = await repo.get_day_schedule(any_group, target_date)

    # Само по себе наличие ответа (пусть даже без пар в этот день) уже подтверждает,
    # что запрос к ИСУ и разбор HTML работают на реальных данных.
    assert result is not None
    assert result.group == any_group.upper()
