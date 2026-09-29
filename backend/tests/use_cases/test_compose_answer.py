from src.use_cases.compose_answer import ComposeAnswer


async def test_prompt_has_original_question_and_all_parts(fake_llm_service) -> None:
    fake_llm_service.response = "Да, можно поспать подольше: первая пара в 10:10."
    use_case = ComposeAnswer(fake_llm_service)

    answer = await use_case.execute(
        "смогу ли я завтра поспать подольше, если пойду сразу в 7-404?",
        ["Завтра первая пара в 10:10, кабинет 7-404.", "Библиотека открыта с 9:00. [Источник: uust.ru]"],
    )

    assert answer == "Да, можно поспать подольше: первая пара в 10:10."
    prompt = fake_llm_service.last_prompt
    assert "смогу ли я завтра поспать подольше" in prompt
    assert "первая пара в 10:10" in prompt
    assert "[Источник: uust.ru]" in prompt
    assert "Источник" in prompt.split("Факты")[0]  # правило сохранять ссылки на источники
