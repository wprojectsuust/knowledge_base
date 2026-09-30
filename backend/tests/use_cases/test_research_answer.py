import json

from src.domain.clarification import ClarificationRequest
from src.domain.data import Data
from src.domain.plan import SearchTask
from src.use_cases.analyze_data import AnalyzeDataByLLMForUser
from src.use_cases.research_answer import ResearchAnswer

DEAN = Data(id=1, source="", content="Декан ФИРТ - Иванов Иван Иванович.")
BIRTHDAY = Data(id=2, source="https://uust.ru/firt", content="Иванов Иван Иванович родился 01.02.1970.")
TASK = SearchTask(question="сколько лет декану ФИРТ", queries=("возраст декана ФИРТ",))


class FakeSearch:
    """Поиск по базе: запрос -> фрагменты; запоминает, что искали."""

    def __init__(self, results: dict[str, list[Data]]) -> None:
        self.results = results
        self.queries: list[list[str]] = []

    async def execute(self, queries: list[str], division: str | None = None) -> list[Data]:
        self.queries.append(queries)
        return [item for query in queries for item in self.results.get(query, [])]


class ScriptedLLM:
    """Отвечает по очереди заготовленными ответами, запоминает промпты."""

    def __init__(self, *responses: str) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []

    async def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.responses.pop(0)


def _research(search, llm, max_extra_searches: int = 2) -> ResearchAnswer:
    return ResearchAnswer(search, AnalyzeDataByLLMForUser(llm), max_extra_searches=max_extra_searches)


async def test_answers_in_one_llm_call_when_first_search_is_enough() -> None:
    llm = ScriptedLLM("Декан ФИРТ - Иванов И. И.")

    answer = await _research(FakeSearch({"возраст декана ФИРТ": [DEAN]}), llm).execute(TASK)

    assert answer == "Декан ФИРТ - Иванов И. И."
    assert len(llm.prompts) == 1


async def test_searches_again_with_llm_queries_and_answers_from_everything_found() -> None:
    search = FakeSearch({"возраст декана ФИРТ": [DEAN], "Иванов Иван Иванович дата рождения": [BIRTHDAY]})
    llm = ScriptedLLM(
        json.dumps({"search": ["Иванов Иван Иванович дата рождения"], "status": "Ищу дату рождения декана"}),
        "Декану ФИРТ 56 лет.",
    )
    statuses: list[str] = []

    async def progress(text: str) -> None:
        statuses.append(text)

    answer = await _research(search, llm).execute(TASK, progress=progress)

    assert answer == "Декану ФИРТ 56 лет."
    assert search.queries[1] == ["Иванов Иван Иванович дата рождения"]
    assert "Ищу дату рождения декана" in statuses
    # на втором шаге LLM видит и декана, и дату рождения - накопленный контекст
    assert DEAN.content in llm.prompts[1] and BIRTHDAY.content in llm.prompts[1]


async def test_last_step_must_answer_without_asking_for_more_searches() -> None:
    search_again = json.dumps({"search": ["ещё запрос"], "status": "Ищу ещё"})
    llm = ScriptedLLM(search_again, search_again, "В базе нет данных о возрасте декана.")

    answer = await _research(FakeSearch({}), llm, max_extra_searches=2).execute(TASK)

    assert answer == "В базе нет данных о возрасте декана."
    assert len(llm.prompts) == 3
    assert '"search"' in llm.prompts[0] and '"search"' not in llm.prompts[2]


async def test_asks_clarification_when_llm_cannot_tell_which_one_is_meant() -> None:
    llm = ScriptedLLM(json.dumps({"clarify": {"field": "faculty", "question": "Декан какого факультета?"}}))

    result = await _research(FakeSearch({}), llm).execute(TASK, can_clarify=True)

    assert result == ClarificationRequest(field="faculty", question="Декан какого факультета?")


async def test_clarification_is_not_offered_when_not_allowed() -> None:
    llm = ScriptedLLM("Декан ФИРТ - Иванов И. И.")

    await _research(FakeSearch({}), llm).execute(TASK, can_clarify=False)

    assert '"clarify"' not in llm.prompts[0]


async def test_repeated_queries_do_not_loop() -> None:
    same = json.dumps({"search": ["возраст декана ФИРТ"], "status": "Ищу снова"})
    llm = ScriptedLLM(same, "Не нашёл.")

    answer = await _research(FakeSearch({}), llm).execute(TASK)

    assert answer == "Не нашёл."
    assert len(llm.prompts) == 2  # тот же запрос второй раз не ищем - сразу просим ответить
