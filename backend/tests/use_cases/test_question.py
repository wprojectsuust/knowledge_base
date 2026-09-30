import json

import pytest

from src.domain.answer import Answer
from src.domain.clarification import ClarificationRequest, KnownFact
from src.domain.dialog import DialogTurn
from src.domain.schedule import DaySchedule
from src.repositories.json_campus_repository import JsonCampusRepository
from src.services.campus_service import CampusService
from src.use_cases.analyze_data import AnalyzeDataByLLMForUser
from src.use_cases.analyze_schedule import AnalyzeScheduleForUser
from src.use_cases.build_route import BuildRoute
from src.use_cases.get_schedule import GetSchedule
from src.use_cases.plan_question import PlanQuestion
from src.use_cases.question import Question
from src.use_cases.search_data import SearchDataByListOfStr

test_question = "Мне сказали что для X нужно пойти в Y, где это?"
GROUP = "1-1.1.1.-26А"


def plan(**parts) -> str:
    return json.dumps({"search": None, "schedule": None, "route": None, "clarify": None, **parts}, ensure_ascii=False)


SEARCH_PLAN = plan(search={"question": test_question, "queries": [test_question]})


@pytest.fixture
def make_question(
    make_fake_llm_service,
    fake_embedding_service,
    fake_vector_search_service,
    fake_data_store_service,
    fake_question_cache_service,
    fake_schedule_service,
    fake_schedule_cache_service,
):
    def _make(planner_response: str | None = SEARCH_PLAN, answer: str = "Ответ из базы.", planner_llm=None) -> Question:
        get_schedule = GetSchedule(
            fake_schedule_service,
            fake_schedule_cache_service,
            fake_embedding_service,
            fake_vector_search_service,
            fake_data_store_service,
            AnalyzeScheduleForUser(make_fake_llm_service("Пары до 12:10.")),
        )
        return Question(
            PlanQuestion(planner_llm if planner_llm is not None else make_fake_llm_service(planner_response)),
            SearchDataByListOfStr(fake_embedding_service, fake_vector_search_service, fake_data_store_service),
            AnalyzeDataByLLMForUser(make_fake_llm_service(answer)),
            fake_question_cache_service,
            get_schedule,
            build_route=BuildRoute(CampusService(JsonCampusRepository())),
        )

    return _make


@pytest.fixture
async def indexed_sample(sample_data, fake_vector_search_service, fake_data_store_service):
    await fake_vector_search_service.index(sample_data.id, [1.0])
    fake_data_store_service.store[sample_data.id] = sample_data
    return sample_data


async def test_answers_plain_question_from_knowledge_base_and_caches_it(
    make_question, indexed_sample, fake_question_cache_service
) -> None:
    result = await make_question(answer="Деканат в корпусе 2.").execute(test_question)

    assert result == Answer(text="Деканат в корпусе 2.")
    assert fake_question_cache_service.store[test_question.strip().lower()] == "Деканат в корпусе 2."


async def test_returns_cached_answer_without_calling_llm(make_question, fake_question_cache_service) -> None:
    fake_question_cache_service.store[test_question.strip().lower()] = "Кэшированный ответ."
    # если пайплайн реально вызовет LLM, тест упадёт на AttributeError у None
    use_case = make_question(planner_llm=None, planner_response=None)
    use_case._plan_question._llm_service = None

    assert await use_case.execute(test_question) == Answer(text="Кэшированный ответ.")


async def test_answers_schedule_and_does_not_cache_it(
    make_question, fake_schedule_service, fake_question_cache_service
) -> None:
    fake_schedule_service.schedules[(GROUP, "2026-09-30")] = DaySchedule(
        group=GROUP, date="2026-09-30", day_label="Среда 30.09.2026", lessons=[]
    )
    use_case = make_question(plan(schedule={"group": GROUP, "date": "2026-09-30", "question": "какие пары"}))

    result = await use_case.execute(f"какое расписание у {GROUP} на 30 сентября")

    assert "Среда 30.09.2026: пар нет." in result.text
    # дата может быть относительной ("завтра") - в общий кэш такое не кладём
    assert fake_question_cache_service.store == {}


async def test_runs_several_tasks_from_one_question_and_combines_answers(
    make_question, indexed_sample, fake_schedule_service, fake_question_cache_service
) -> None:
    fake_schedule_service.schedules[(GROUP, "2026-09-30")] = DaySchedule(
        group=GROUP, date="2026-09-30", day_label="Среда 30.09.2026", lessons=[]
    )
    use_case = make_question(
        plan(
            search={"question": "где деканат", "queries": ["где деканат"]},
            schedule={"group": GROUP, "date": "2026-09-30", "question": "какие пары"},
            route={"from": None, "to": "7-404"},
        ),
        answer="Деканат в корпусе 2.",
    )

    result = await use_case.execute("какие пары 30 сентября, где деканат и как пройти в 7-404")

    assert "пар нет" in result.text
    assert "Деканат в корпусе 2." in result.text
    assert "7-404" in result.text
    assert result.route is not None and result.route.points[-1].floor == 4
    assert fake_question_cache_service.store == {}


async def test_returns_clarification_request_and_does_not_cache_it(make_question, fake_question_cache_service) -> None:
    use_case = make_question(plan(clarify={"field": "group", "question": "В какой группе вы учитесь?"}))

    result = await use_case.execute("какое у меня завтра расписание")

    assert result == ClarificationRequest(field="group", question="В какой группе вы учитесь?")
    assert fake_question_cache_service.store == {}


async def test_passes_known_facts_to_planner(make_question, make_fake_llm_service) -> None:
    planner = make_fake_llm_service(SEARCH_PLAN)

    await make_question(planner_llm=planner).execute(
        "какое у меня завтра расписание", facts=[KnownFact(field="group", value="ПРО-101")]
    )

    assert "ПРО-101" in planner.last_prompt


async def test_ignores_repeated_clarification_of_known_field(make_question, indexed_sample) -> None:
    # защита от зацикливания: студент уже назвал группу, а LLM всё равно переспрашивает
    use_case = make_question(
        plan(clarify={"field": "group", "question": "В какой группе вы учитесь?"}), answer="Обычный ответ из базы знаний."
    )

    result = await use_case.execute("где деканат", facts=[KnownFact(field="group", value="ПРО-101")])

    assert result == Answer(text="Обычный ответ из базы знаний.")


async def test_builds_route(make_question) -> None:
    result = await make_question(plan(route={"from": "kpp", "to": "7-404"})).execute("как пройти в 7-404")

    assert result.route is not None
    assert "4 этаж" in result.text


async def test_explains_unknown_route_target_without_unrelated_example(make_question) -> None:
    result = await make_question(plan(route={"from": None, "to": "бассейн"})).execute("как дойти до бассейна")

    assert result.route is None
    assert "бассейн" in result.text  # называем то, что не нашли
    assert "7-404" not in result.text


async def test_follow_up_with_history_bypasses_cache_and_reaches_planner(
    make_question, make_fake_llm_service, indexed_sample, fake_question_cache_service
) -> None:
    # тот же текст вопроса уже в кэше, но с историей он может значить другое ("а туда как пройти?")
    fake_question_cache_service.store[test_question.strip().lower()] = "Ответ без учёта контекста."
    planner = make_fake_llm_service(SEARCH_PLAN)
    history = [DialogTurn(question="где деканат ФИРТ", answer="В корпусе 2.")]

    result = await make_question(planner_llm=planner, answer="С учётом контекста.").execute(test_question, history=history)

    assert result == Answer(text="С учётом контекста.")
    assert "В корпусе 2." in planner.last_prompt


async def test_several_parts_are_composed_into_one_answer_to_the_original_question(
    make_question, make_fake_llm_service, indexed_sample, fake_schedule_service
) -> None:
    from src.use_cases.compose_answer import ComposeAnswer

    fake_schedule_service.schedules[(GROUP, "2026-09-30")] = DaySchedule(
        group=GROUP, date="2026-09-30", day_label="Среда 30.09.2026", lessons=[]
    )
    composer_llm = make_fake_llm_service("Да, поспать можно: пар нет. Маршрут ниже.")
    use_case = make_question(
        plan(
            search={"question": "где деканат", "queries": ["где деканат"]},
            schedule={"group": GROUP, "date": "2026-09-30", "question": "смогу ли я поспать подольше"},
            route={"from": None, "to": "7-404"},
        ),
        answer="Деканат в корпусе 2.",
    )
    use_case._compose_answer = ComposeAnswer(composer_llm)

    result = await use_case.execute("смогу ли я поспать подольше, где деканат и как пройти в 7-404")

    assert result.text.startswith("Да, поспать можно: пар нет.")
    # маршрут не пересказывается ИИ - шаблонный текст идёт как есть
    assert "Поднимитесь по лестнице на 4 этаж" in result.text
    assert "Деканат в корпусе 2." in composer_llm.last_prompt
    assert "пар нет" in composer_llm.last_prompt


async def test_single_part_is_not_recomposed(make_question, make_fake_llm_service, indexed_sample) -> None:
    from src.use_cases.compose_answer import ComposeAnswer

    composer_llm = make_fake_llm_service("не должно вызываться")
    use_case = make_question(answer="Деканат в корпусе 2.")
    use_case._compose_answer = ComposeAnswer(composer_llm)

    await use_case.execute(test_question)

    assert composer_llm.call_count == 0


async def test_falls_back_to_joined_parts_when_composing_fails(
    make_question, indexed_sample, fake_schedule_service
) -> None:
    from src.services.llm_service import LLMUnavailableError

    class _BrokenComposer:
        async def execute(self, question, parts):
            raise LLMUnavailableError("503")

    fake_schedule_service.schedules[(GROUP, "2026-09-30")] = DaySchedule(
        group=GROUP, date="2026-09-30", day_label="Среда 30.09.2026", lessons=[]
    )
    use_case = make_question(
        plan(
            search={"question": "где деканат", "queries": ["где деканат"]},
            schedule={"group": GROUP, "date": "2026-09-30", "question": "какие пары"},
        ),
        answer="Деканат в корпусе 2.",
    )
    use_case._compose_answer = _BrokenComposer()

    result = await use_case.execute("какие пары и где деканат")

    assert "пар нет" in result.text and "Деканат в корпусе 2." in result.text


async def test_reports_progress_while_answering(make_question, indexed_sample) -> None:
    statuses: list[str] = []

    async def progress(text: str) -> None:
        statuses.append(text)

    await make_question(answer="Деканат в корпусе 2.").execute(test_question, progress=progress)

    assert statuses[0] == "Разбираю вопрос"
    assert "Ищу в базе знаний" in statuses


async def test_search_can_ask_for_clarification_and_it_is_not_cached(
    make_question, indexed_sample, fake_question_cache_service
) -> None:
    clarify = json.dumps({"clarify": {"field": "faculty", "question": "Какого факультета?"}}, ensure_ascii=False)

    result = await make_question(answer=clarify).execute(test_question)

    assert result == ClarificationRequest(field="faculty", question="Какого факультета?")
    assert fake_question_cache_service.store == {}


async def test_search_does_not_clarify_again_once_facts_are_given(make_question, indexed_sample) -> None:
    clarify = json.dumps({"clarify": {"field": "faculty", "question": "Какого факультета?"}}, ensure_ascii=False)

    result = await make_question(answer=clarify).execute(test_question, facts=[KnownFact(field="faculty", value="ФИРТ")])

    assert not isinstance(result, ClarificationRequest)


async def test_trivial_follow_up_skips_search_and_is_not_cached(
    make_question, indexed_sample, fake_embedding_service, fake_question_cache_service
) -> None:
    history = [DialogTurn(question="когда кончаются пары?", answer="Последняя пара заканчивается в 15:25.")]
    use_case = make_question(planner_response=plan(reply="Через 2 часа 15 минут."), answer="НЕ ДОЛЖНО ВЫЗВАТЬСЯ")

    result = await use_case.execute("через сколько это?", history=history)

    assert result == Answer(text="Через 2 часа 15 минут.")
    assert fake_embedding_service.call_count == 0  # в векторную базу не ходили
    assert fake_question_cache_service.store == {}


async def test_falls_back_to_knowledge_base_when_place_is_not_on_the_map(make_question, indexed_sample) -> None:
    use_case = make_question(
        planner_response=plan(route={"from": None, "to": "главный корпус БашГУ"}),
        answer="Главный корпус - ул. Заки Валиди, 32.",
    )

    result = await use_case.execute("как добраться до главного корпуса?")

    assert result.route is None
    assert result.text.startswith("Главный корпус - ул. Заки Валиди, 32.")  # ответ из базы знаний
    assert "не отмечено" in result.text  # и честно - почему без маршрута
