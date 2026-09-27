from src.use_cases.analyze_data import AnalyzeDataByLLMForNewData, AnalyzeDataByLLMForUser


def test_analyze_data_by_llm_for_user_returns_llm_answer(sample_data, fake_llm_service) -> None:
    fake_llm_service.response = "В корпусе 2, деканат."
    use_case = AnalyzeDataByLLMForUser(fake_llm_service)

    result = use_case.execute(prompt="Где деканат?", data=[sample_data])

    assert result == "В корпусе 2, деканат."
    assert "Где деканат?" in fake_llm_service.last_prompt
    assert sample_data.content in fake_llm_service.last_prompt


def test_analyze_data_by_llm_for_new_data_returns_generated_questions(sample_data, fake_llm_service) -> None:
    fake_llm_service.response = '["где деканат", "как найти деканат"]'
    use_case = AnalyzeDataByLLMForNewData(fake_llm_service)

    assert use_case.execute(sample_data) == ["где деканат", "как найти деканат"]
