from src.domain.schedule import DaySchedule
from src.domain.clarification import ClarificationRequest, KnownFact
from src.use_cases.analyze_data import AnalyzeDataByLLMForUser
from src.use_cases.get_really_questions import GetReallyQuestions
from src.use_cases.analyze_schedule import AnalyzeScheduleForUser
from src.use_cases.get_schedule import GetSchedule
from src.use_cases.question import Question
from src.use_cases.search_data import SearchDataByListOfStr

test_question = "Мне сказали что для X нужно пойти в Y, где это?"


def _build_use_case(
    make_fake_llm_service,
    fake_embedding_service,
    fake_vector_search_service,
    fake_data_store_service,
    fake_question_cache_service,
    fake_schedule_service,
    fake_schedule_cache_service,
    answer: str,
    llm_response: str | None = None,
) -> Question:
    get_really_questions = GetReallyQuestions(make_fake_llm_service(llm_response or f'["{test_question}"]'))
    search_data = SearchDataByListOfStr(fake_embedding_service, fake_vector_search_service, fake_data_store_service)
    analyze_data = AnalyzeDataByLLMForUser(make_fake_llm_service(answer))
    get_schedule = GetSchedule(
        fake_schedule_service,
        fake_schedule_cache_service,
        fake_embedding_service,
        fake_vector_search_service,
        fake_data_store_service,
        AnalyzeScheduleForUser(make_fake_llm_service(answer)),
    )
    return Question(get_really_questions, search_data, analyze_data, fake_question_cache_service, get_schedule)


async def test_question_orchestrates_full_flow(
    sample_data,
    make_fake_llm_service,
    fake_embedding_service,
    fake_vector_search_service,
    fake_data_store_service,
    fake_question_cache_service,
    fake_schedule_service,
    fake_schedule_cache_service,
) -> None:
    await fake_vector_search_service.index(sample_data.id, [1.0])
    fake_data_store_service.store[sample_data.id] = sample_data

    use_case = _build_use_case(
        make_fake_llm_service,
        fake_embedding_service,
        fake_vector_search_service,
        fake_data_store_service,
        fake_question_cache_service,
        fake_schedule_service,
        fake_schedule_cache_service,
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
    fake_schedule_service,
    fake_schedule_cache_service,
) -> None:
    await fake_vector_search_service.index(sample_data.id, [1.0])
    fake_data_store_service.store[sample_data.id] = sample_data

    use_case = _build_use_case(
        make_fake_llm_service,
        fake_embedding_service,
        fake_vector_search_service,
        fake_data_store_service,
        fake_question_cache_service,
        fake_schedule_service,
        fake_schedule_cache_service,
        answer="Деканат находится в корпусе 2.",
    )

    await use_case.execute(question=test_question)

    assert fake_question_cache_service.store[test_question.strip().lower()] == "Деканат находится в корпусе 2."


async def test_question_returns_cached_answer_without_running_pipeline(
    fake_embedding_service,
    fake_vector_search_service,
    fake_data_store_service,
    fake_question_cache_service,
    fake_schedule_service,
    fake_schedule_cache_service,
) -> None:
    fake_question_cache_service.store[test_question.strip().lower()] = "Кэшированный ответ."

    llm_that_must_not_be_called = None  # если пайплайн реально вызовет LLM, тест упадёт на AttributeError
    get_really_questions = GetReallyQuestions(llm_that_must_not_be_called)
    search_data = SearchDataByListOfStr(fake_embedding_service, fake_vector_search_service, fake_data_store_service)
    analyze_data = AnalyzeDataByLLMForUser(llm_that_must_not_be_called)
    get_schedule = GetSchedule(
        fake_schedule_service,
        fake_schedule_cache_service,
        fake_embedding_service,
        fake_vector_search_service,
        fake_data_store_service,
        AnalyzeScheduleForUser(llm_that_must_not_be_called),
    )
    use_case = Question(get_really_questions, search_data, analyze_data, fake_question_cache_service, get_schedule)

    answer = await use_case.execute(question=test_question)

    assert answer == "Кэшированный ответ."


async def test_question_dispatches_to_schedule_when_marker_detected(
    make_fake_llm_service,
    fake_embedding_service,
    fake_vector_search_service,
    fake_data_store_service,
    fake_question_cache_service,
    fake_schedule_service,
    fake_schedule_cache_service,
) -> None:
    schedule_question = "какое расписание у 1-1.1.1.-26А на 30 сентября"
    fake_schedule_service.schedules[("1-1.1.1.-26А", "2026-09-30")] = DaySchedule(
        group="1-1.1.1.-26А", date="2026-09-30", day_label="Среда 30.09.2026", lessons=[]
    )

    use_case = _build_use_case(
        make_fake_llm_service,
        fake_embedding_service,
        fake_vector_search_service,
        fake_data_store_service,
        fake_question_cache_service,
        fake_schedule_service,
        fake_schedule_cache_service,
        answer="не должно вызываться",
        llm_response="rasp-1-1.1.1.-26А-2026-09-30",
    )

    answer = await use_case.execute(question=schedule_question)

    assert "Среда 30.09.2026" in answer
    # ответ про расписание не должен попадать в обычный кэш вопрос-ответ (дата может быть
    # относительной, тот же текст завтра значит другой день)
    assert schedule_question.strip().lower() not in fake_question_cache_service.store


async def test_question_returns_clarification_request_and_does_not_cache_it(
    make_fake_llm_service,
    fake_embedding_service,
    fake_vector_search_service,
    fake_data_store_service,
    fake_question_cache_service,
    fake_schedule_service,
    fake_schedule_cache_service,
) -> None:
    use_case = _build_use_case(
        make_fake_llm_service,
        fake_embedding_service,
        fake_vector_search_service,
        fake_data_store_service,
        fake_question_cache_service,
        fake_schedule_service,
        fake_schedule_cache_service,
        answer="не должно вызываться",
        llm_response="clarify-group: В какой группе вы учитесь?",
    )

    result = await use_case.execute(question="какое у меня завтра расписание")

    assert result == ClarificationRequest(field="group", question="В какой группе вы учитесь?")
    assert fake_question_cache_service.store == {}


async def test_question_passes_known_facts_to_llm(
    make_fake_llm_service,
    fake_embedding_service,
    fake_vector_search_service,
    fake_data_store_service,
    fake_question_cache_service,
    fake_schedule_service,
    fake_schedule_cache_service,
) -> None:
    llm = make_fake_llm_service("rasp-ПРО-101-2026-09-29")
    fake_schedule_service.schedules[("ПРО-101", "2026-09-29")] = DaySchedule(
        group="ПРО-101", date="2026-09-29", day_label="Вторник 29.09.2026", lessons=[]
    )
    get_schedule = GetSchedule(
        fake_schedule_service,
        fake_schedule_cache_service,
        fake_embedding_service,
        fake_vector_search_service,
        fake_data_store_service,
        AnalyzeScheduleForUser(make_fake_llm_service("")),
    )
    use_case = Question(
        GetReallyQuestions(llm),
        SearchDataByListOfStr(fake_embedding_service, fake_vector_search_service, fake_data_store_service),
        AnalyzeDataByLLMForUser(make_fake_llm_service("")),
        fake_question_cache_service,
        get_schedule,
    )

    answer = await use_case.execute(
        question="какое у меня завтра расписание", facts=[KnownFact(field="group", value="ПРО-101")]
    )

    assert "ПРО-101" in llm.last_prompt
    assert answer == "Вторник 29.09.2026: пар нет."


async def test_question_ignores_repeated_clarification_of_known_field(
    sample_data,
    make_fake_llm_service,
    fake_embedding_service,
    fake_vector_search_service,
    fake_data_store_service,
    fake_question_cache_service,
    fake_schedule_service,
    fake_schedule_cache_service,
) -> None:
    # защита от зацикливания: студент уже назвал группу, а LLM всё равно переспрашивает
    await fake_vector_search_service.index(sample_data.id, [1.0])
    fake_data_store_service.store[sample_data.id] = sample_data
    use_case = _build_use_case(
        make_fake_llm_service,
        fake_embedding_service,
        fake_vector_search_service,
        fake_data_store_service,
        fake_question_cache_service,
        fake_schedule_service,
        fake_schedule_cache_service,
        answer="Обычный ответ из базы знаний.",
        llm_response="clarify-group: В какой группе вы учитесь?",
    )

    answer = await use_case.execute(question="где деканат", facts=[KnownFact(field="group", value="ПРО-101")])

    assert answer == "Обычный ответ из базы знаний."


async def test_question_builds_route_when_llm_asks_for_navigation(
    make_fake_llm_service,
    fake_embedding_service,
    fake_vector_search_service,
    fake_data_store_service,
    fake_question_cache_service,
    fake_schedule_service,
    fake_schedule_cache_service,
) -> None:
    from src.domain.campus import Route
    from src.repositories.json_campus_repository import JsonCampusRepository
    from src.services.campus_service import CampusService
    from src.use_cases.build_route import BuildRoute

    get_schedule = GetSchedule(
        fake_schedule_service,
        fake_schedule_cache_service,
        fake_embedding_service,
        fake_vector_search_service,
        fake_data_store_service,
        AnalyzeScheduleForUser(make_fake_llm_service("")),
    )
    use_case = Question(
        GetReallyQuestions(make_fake_llm_service("route: kpp -> 7-404")),
        SearchDataByListOfStr(fake_embedding_service, fake_vector_search_service, fake_data_store_service),
        AnalyzeDataByLLMForUser(make_fake_llm_service("не должно вызываться")),
        fake_question_cache_service,
        get_schedule,
        build_route=BuildRoute(CampusService(JsonCampusRepository())),
    )

    result = await use_case.execute(question="как пройти в 7-404")

    assert isinstance(result, Route)
    assert "4 этаж" in result.text()
    assert fake_question_cache_service.store == {}
