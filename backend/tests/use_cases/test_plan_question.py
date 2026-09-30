import json

from src.domain.clarification import ClarificationRequest
from src.domain.dialog import DialogTurn
from src.domain.plan import QuestionPlan, SearchTask
from src.domain.route import RouteRequest
from src.domain.schedule import ScheduleRequest
from src.use_cases.plan_question import PlanQuestion


def _plan(**parts) -> str:
    return json.dumps({"search": None, "schedule": None, "route": None, "clarify": None, **parts}, ensure_ascii=False)


async def test_parses_plan_with_several_tasks_at_once(fake_llm_service) -> None:
    fake_llm_service.response = _plan(
        search={"question": "где находится деканат", "queries": ["где деканат", "адрес деканата"]},
        schedule={"group": "ТОП-106Б", "date": "2026-09-29", "question": "во сколько кончаются пары"},
        route={"from": None, "to": "7-404"},
    )

    plan = await PlanQuestion(fake_llm_service).execute("какие завтра пары у ТОП-106Б, где деканат и как пройти в 7-404")

    assert plan == QuestionPlan(
        search=SearchTask(question="где находится деканат", queries=("где деканат", "адрес деканата")),
        schedule=ScheduleRequest(group="ТОП-106Б", date="2026-09-29", question="во сколько кончаются пары"),
        route=RouteRequest(source=None, target="7-404"),
    )


async def test_parses_clarification(fake_llm_service) -> None:
    fake_llm_service.response = _plan(clarify={"field": "group", "question": "В какой группе вы учитесь?"})

    plan = await PlanQuestion(fake_llm_service).execute("какое у меня завтра расписание")

    assert plan.clarification == ClarificationRequest(field="group", question="В какой группе вы учитесь?")


async def test_accepts_json_wrapped_in_markdown_fence(fake_llm_service) -> None:
    fake_llm_service.response = "```json\n" + _plan(route={"from": "7-404", "to": "1-101"}) + "\n```"

    plan = await PlanQuestion(fake_llm_service).execute("как пройти из 7-404 в 1-101")

    assert plan.route == RouteRequest(source="7-404", target="1-101")


async def test_falls_back_to_plain_search_when_llm_breaks_format(fake_llm_service) -> None:
    fake_llm_service.response = "извините, не понял"

    plan = await PlanQuestion(fake_llm_service).execute("где деканат")

    assert plan == QuestionPlan(search=SearchTask(question="где деканат", queries=("где деканат",)))


async def test_drops_schedule_with_malformed_date(fake_llm_service) -> None:
    fake_llm_service.response = _plan(schedule={"group": "ТОП-106Б", "date": "завтра", "question": "пары"})

    plan = await PlanQuestion(fake_llm_service).execute("какие завтра пары у ТОП-106Б")

    assert plan.schedule is None


async def test_clarification_is_ignored_and_not_offered_when_not_allowed(fake_llm_service) -> None:
    fake_llm_service.response = _plan(clarify={"field": "group", "question": "Группа?"})
    use_case = PlanQuestion(fake_llm_service)

    plan = await use_case.execute("какое у меня расписание", can_clarify=False)

    assert plan.clarification is None
    assert '"clarify"' not in fake_llm_service.last_prompt


async def test_prompt_contains_message_hints_and_rules(fake_llm_service) -> None:
    fake_llm_service.response = _plan()
    use_case = PlanQuestion(fake_llm_service, places_hint="Библиотека -> place:library")

    await use_case.execute("как узнать расписание своей группы")

    prompt = fake_llm_service.last_prompt
    assert "place:library" in prompt
    assert "ТОП-106Б" in prompt  # пример приведения группы к формату справочника
    # фраза встречается дважды: в самом сообщении и как пример "не уточнять" в инструкции
    assert prompt.lower().count("как узнать расписание своей группы") >= 2


async def test_prompt_includes_dialog_history_for_follow_ups(fake_llm_service) -> None:
    fake_llm_service.response = _plan()
    history = [DialogTurn(question="где деканат ФИРТ", answer="Деканат ФИРТ в корпусе 2, кабинет 214.")]

    await PlanQuestion(fake_llm_service).execute("а как туда пройти?", history=history)

    assert "Деканат ФИРТ в корпусе 2" in fake_llm_service.last_prompt


async def test_today_is_taken_in_ufa_timezone(fake_llm_service, monkeypatch) -> None:
    import datetime as dt

    from src.use_cases import plan_question

    class _FixedDatetime(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            # 22:00 UTC 29 сентября = 03:00 30 сентября в Уфе (UTC+5)
            return dt.datetime(2026, 9, 29, 22, 0, tzinfo=dt.timezone.utc).astimezone(tz)

    monkeypatch.setattr(plan_question, "datetime", _FixedDatetime)
    fake_llm_service.response = _plan()

    await PlanQuestion(fake_llm_service).execute("какие у меня завтра пары")

    assert "Сегодня 2026-09-30" in fake_llm_service.last_prompt


async def test_trivial_follow_up_is_answered_by_planner_itself(fake_llm_service) -> None:
    fake_llm_service.response = _plan(reply="Пары закончатся через 2 часа 15 минут, в 15:25.")
    history = [DialogTurn(question="когда кончаются пары у ТОП-106Б?", answer="Последняя пара заканчивается в 15:25.")]

    plan = await PlanQuestion(fake_llm_service).execute("через сколько это?", history=history)

    assert plan == QuestionPlan(reply="Пары закончатся через 2 часа 15 минут, в 15:25.")


async def test_reply_is_dropped_when_message_also_needs_the_knowledge_base(fake_llm_service) -> None:
    # «спасибо, а где деканат?» - вежливость не должна съесть вопрос о вузе
    fake_llm_service.response = _plan(
        reply="Пожалуйста!", search={"question": "где деканат", "queries": ["где деканат"]}
    )

    plan = await PlanQuestion(fake_llm_service).execute("спасибо, а где деканат?")

    assert plan.reply is None
    assert plan.search is not None


async def test_prompt_explains_when_not_to_go_to_the_knowledge_base(fake_llm_service) -> None:
    fake_llm_service.response = _plan()

    await PlanQuestion(fake_llm_service).execute("через сколько это?")

    prompt = fake_llm_service.last_prompt
    assert '"reply"' in prompt
    assert "из диалога" in prompt  # тривиальный - только то, что выводится из прошлых реплик
    assert "не отвечай сам" in prompt.lower()  # факты о вузе - только из базы, даже если модель «знает»


async def test_prompt_has_current_time_for_how_long_questions(fake_llm_service, monkeypatch) -> None:
    import datetime as dt

    from src.use_cases import plan_question

    class _FixedDatetime(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return dt.datetime(2026, 9, 30, 8, 10, tzinfo=dt.timezone.utc).astimezone(tz)  # 13:10 в Уфе

    monkeypatch.setattr(plan_question, "datetime", _FixedDatetime)
    fake_llm_service.response = _plan()

    await PlanQuestion(fake_llm_service).execute("через сколько это?")

    assert "13:10" in fake_llm_service.last_prompt
