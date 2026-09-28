from src.use_cases.analyze_data import AnalyzeDataByLLMForNewData, AnalyzeDataByLLMForUser


async def test_analyze_data_by_llm_for_user_returns_llm_answer(sample_data, fake_llm_service) -> None:
    fake_llm_service.response = "В корпусе 2, деканат."
    use_case = AnalyzeDataByLLMForUser(fake_llm_service)

    result = await use_case.execute(prompt="Где деканат?", data=[sample_data])

    assert result == "В корпусе 2, деканат."
    assert "Где деканат?" in fake_llm_service.last_prompt
    assert sample_data.content in fake_llm_service.last_prompt


async def test_analyze_data_by_llm_for_new_data_returns_generated_questions(sample_data, fake_llm_service) -> None:
    fake_llm_service.response = '["где деканат", "как найти деканат"]'
    use_case = AnalyzeDataByLLMForNewData(fake_llm_service)

    assert await use_case.execute(sample_data) == ["где деканат", "как найти деканат"]


async def test_analyze_data_for_user_prompt_forbids_off_topic_facts_and_suggests_whom_to_ask(
    sample_data, fake_llm_service
) -> None:
    from src.use_cases.analyze_data import AnalyzeDataByLLMForUser

    await AnalyzeDataByLLMForUser(fake_llm_service).execute("что делать, если пропустил пару?", [sample_data])

    prompt = fake_llm_service.last_prompt.lower()
    assert "не относ" in prompt  # нерелевантные фрагменты - игнорировать
    assert "тьютор" in prompt  # куда обратиться, если ответа в базе нет
