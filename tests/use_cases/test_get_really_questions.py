from src.use_cases.get_really_questions import GetReallyQuestions


def test_extracts_questions_from_llm_json_response(fake_llm_service) -> None:
    fake_llm_service.response = '["Где находится деканат?"]'
    use_case = GetReallyQuestions(fake_llm_service)

    result = use_case.execute(question="Мне сказали что для X нужно пойти в Y, где это?")

    assert result == ["Где находится деканат?"]


def test_returns_empty_list_when_llm_gives_nothing_useful(fake_llm_service) -> None:
    fake_llm_service.response = "[]"
    use_case = GetReallyQuestions(fake_llm_service)

    assert use_case.execute(question="привет") == []
