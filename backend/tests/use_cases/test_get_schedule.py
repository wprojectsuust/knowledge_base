from src.domain.schedule import DaySchedule, ScheduleLesson
from src.use_cases.get_schedule import GetSchedule

sample_schedule = DaySchedule(
    group="1-1.1.1.-26А",
    date="2026-09-30",
    day_label="Среда 30.09.2026",
    lessons=[
        ScheduleLesson(time="09:00-10:30", subject="Матанализ", venue="ауд. 305"),
        ScheduleLesson(time="10:40-12:10", subject="Физика", venue=None),
    ],
)


def _build_use_case(fake_schedule_service, fake_schedule_cache_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service) -> GetSchedule:
    return GetSchedule(
        fake_schedule_service,
        fake_schedule_cache_service,
        fake_embedding_service,
        fake_vector_search_service,
        fake_data_store_service,
    )


async def test_returns_not_found_message_when_schedule_missing(
    fake_schedule_service, fake_schedule_cache_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    use_case = _build_use_case(
        fake_schedule_service, fake_schedule_cache_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
    )

    answer = await use_case.execute("НЕИЗВЕСТНАЯ-ГРУППА", "2026-09-30")

    assert "не удалось найти расписание" in answer.lower()


async def test_formats_lessons_and_saves_to_cache_on_miss(
    fake_schedule_service, fake_schedule_cache_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    fake_schedule_service.schedules[("1-1.1.1.-26А", "2026-09-30")] = sample_schedule
    use_case = _build_use_case(
        fake_schedule_service, fake_schedule_cache_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
    )

    answer = await use_case.execute("1-1.1.1.-26А", "2026-09-30")

    assert "Матанализ" in answer
    assert "ауд. 305" in answer
    assert "Физика" in answer
    assert fake_schedule_cache_service.store[("1-1.1.1.-26А", "2026-09-30")] == sample_schedule


async def test_uses_cache_without_calling_schedule_service(
    fake_schedule_service, fake_schedule_cache_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    fake_schedule_cache_service.store[("1-1.1.1.-26А", "2026-09-30")] = sample_schedule
    use_case = _build_use_case(
        fake_schedule_service, fake_schedule_cache_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
    )

    answer = await use_case.execute("1-1.1.1.-26А", "2026-09-30")

    assert "Матанализ" in answer
    assert fake_schedule_service.call_count == 0


async def test_adds_directions_when_similarity_above_threshold(
    sample_data, fake_schedule_service, fake_schedule_cache_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    schedule_with_venue = DaySchedule(
        group="1-1.1.1.-26А",
        date="2026-09-30",
        day_label="Среда 30.09.2026",
        lessons=[ScheduleLesson(time="09:00", subject="Матанализ", venue="ауд. 305")],
    )
    fake_schedule_service.schedules[("1-1.1.1.-26А", "2026-09-30")] = schedule_with_venue

    directions_data = sample_data.__class__(id=1, source="uust.ru", content="Идите налево от главного входа.")
    await fake_vector_search_service.index(1, [1.0])
    fake_vector_search_service.scores[1] = 0.9
    fake_data_store_service.store[1] = directions_data

    use_case = _build_use_case(
        fake_schedule_service, fake_schedule_cache_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
    )

    answer = await use_case.execute("1-1.1.1.-26А", "2026-09-30")

    assert "Как добраться" in answer
    assert "Идите налево от главного входа." in answer


async def test_skips_directions_when_similarity_below_threshold(
    fake_schedule_service, fake_schedule_cache_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    schedule_with_venue = DaySchedule(
        group="1-1.1.1.-26А",
        date="2026-09-30",
        day_label="Среда 30.09.2026",
        lessons=[ScheduleLesson(time="09:00", subject="Матанализ", venue="ауд. 305")],
    )
    fake_schedule_service.schedules[("1-1.1.1.-26А", "2026-09-30")] = schedule_with_venue

    await fake_vector_search_service.index(1, [1.0])
    fake_vector_search_service.scores[1] = 0.1  # ниже порога

    use_case = _build_use_case(
        fake_schedule_service, fake_schedule_cache_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
    )

    answer = await use_case.execute("1-1.1.1.-26А", "2026-09-30")

    assert "Как добраться" not in answer
