from src.domain.schedule import ScheduleRequest
from src.domain.clarification import ClarificationRequest
from src.use_cases.get_really_questions import GetReallyQuestions


async def test_extracts_questions_from_llm_json_response(fake_llm_service) -> None:
    fake_llm_service.response = '["Где находится деканат?"]'
    use_case = GetReallyQuestions(fake_llm_service)

    result = await use_case.execute(question="Мне сказали что для X нужно пойти в Y, где это?")

    assert result == ["Где находится деканат?"]


async def test_prompt_includes_the_actual_user_message(fake_llm_service) -> None:
    fake_llm_service.response = "[]"
    use_case = GetReallyQuestions(fake_llm_service)

    await use_case.execute(question="Где находится деканат?")

    assert "Где находится деканат?" in fake_llm_service.last_prompt


async def test_returns_empty_list_when_llm_gives_nothing_useful(fake_llm_service) -> None:
    fake_llm_service.response = "[]"
    use_case = GetReallyQuestions(fake_llm_service)

    assert await use_case.execute(question="привет") == []


async def test_detects_schedule_request_from_marker(fake_llm_service) -> None:
    fake_llm_service.response = "rasp-1-1.1.1.-26А-2026-09-30"
    use_case = GetReallyQuestions(fake_llm_service)

    result = await use_case.execute(question="какое расписание у 1-1.1.1.-26А на 30 сентября")

    assert result == ScheduleRequest(group="1-1.1.1.-26А", date="2026-09-30")


async def test_detects_clarification_request_from_marker(fake_llm_service) -> None:
    fake_llm_service.response = "clarify-group: В какой группе вы учитесь?"
    use_case = GetReallyQuestions(fake_llm_service)

    result = await use_case.execute(question="какое у меня завтра расписание")

    assert result == ClarificationRequest(field="group", question="В какой группе вы учитесь?")


async def test_prompt_offers_clarification_only_when_allowed(fake_llm_service) -> None:
    fake_llm_service.response = "[]"
    use_case = GetReallyQuestions(fake_llm_service)

    await use_case.execute(question="какое у меня завтра расписание", can_clarify=True)
    assert "clarify-" in fake_llm_service.last_prompt

    await use_case.execute(question="какое у меня завтра расписание", can_clarify=False)
    assert "clarify-" not in fake_llm_service.last_prompt
