from src.use_cases.analyze_data import AnalyzeDataByLLMForUser
from src.use_cases.get_really_questions import GetReallyQuestions
from src.use_cases.question import Question
from src.use_cases.search_data import SearchDataByListOfStr

test_question = "Мне сказали что для X нужно пойти в Y, где это?"


def _build_use_case(
    make_fake_llm_service,
    fake_embedding_service,
    fake_vector_search_service,
    fake_data_store_service,
    fake_question_cache_service,
    answer: str,
) -> Question:
    get_really_questions = GetReallyQuestions(make_fake_llm_service(f'["{test_question}"]'))
    search_data = SearchDataByListOfStr(fake_embedding_service, fake_vector_search_service, fake_data_store_service)
    analyze_data = AnalyzeDataByLLMForUser(make_fake_llm_service(answer))
    return Question(get_really_questions, search_data, analyze_data, fake_question_cache_service)


async def test_question_orchestrates_full_flow(
    sample_data,
    make_fake_llm_service,
    fake_embedding_service,
    fake_vector_search_service,
    fake_data_store_service,
    fake_question_cache_service,
) -> None:
    await fake_vector_search_service.index(sample_data.id, [1.0])
    fake_data_store_service.store[sample_data.id] = sample_data

    use_case = _build_use_case(
        make_fake_llm_service,
        fake_embedding_service,
        fake_vector_search_service,
        fake_data_store_service,
        fake_question_cache_service,
        answer="Деканат находится в корпусе 2, приходите пешком.",
    )

    answer = await use_case.execute(question=test_question)

    assert answer == "Деканат находится в корпусе 2, приходите пешком."


async def test_question_caches_answer_after_computing_it(
    sample_data,
    make_fake_llm_service,
    fake_embedding_service,
    fake_vector_search_service,
    fake_data_store_service,
    fake_question_cache_service,
) -> None:
    await fake_vector_search_service.index(sample_data.id, [1.0])
    fake_data_store_service.store[sample_data.id] = sample_data

    use_case = _build_use_case(
        make_fake_llm_service,
        fake_embedding_service,
        fake_vector_search_service,
        fake_data_store_service,
        fake_question_cache_service,
        answer="Деканат находится в корпусе 2.",
    )

    await use_case.execute(question=test_question)

    assert fake_question_cache_service.store[test_question.strip().lower()] == "Деканат находится в корпусе 2."


async def test_question_returns_cached_answer_without_running_pipeline(
    fake_embedding_service, fake_vector_search_service, fake_data_store_service, fake_question_cache_service
) -> None:
    fake_question_cache_service.store[test_question.strip().lower()] = "Кэшированный ответ."

    llm_that_must_not_be_called = None  # если пайплайн реально вызовет LLM, тест упадёт на AttributeError
    get_really_questions = GetReallyQuestions(llm_that_must_not_be_called)
    search_data = SearchDataByListOfStr(fake_embedding_service, fake_vector_search_service, fake_data_store_service)
    analyze_data = AnalyzeDataByLLMForUser(llm_that_must_not_be_called)
    use_case = Question(get_really_questions, search_data, analyze_data, fake_question_cache_service)

    answer = await use_case.execute(question=test_question)

    assert answer == "Кэшированный ответ."
