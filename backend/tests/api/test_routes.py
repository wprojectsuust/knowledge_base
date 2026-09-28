from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.dependencies import (
    get_new_data_use_case,
    get_question_use_case,
    get_remove_data_use_case,
    get_search_data_by_id_use_case,
    get_search_data_use_case,
)
from src.domain.answer import Answer
from src.domain.clarification import ClarificationRequest
from src.domain.data import Data
from src.domain.dialog import DialogTurn
from src.use_cases.analyze_data import AnalyzeDataByLLMForUser
from src.use_cases.analyze_schedule import AnalyzeScheduleForUser
from src.use_cases.get_schedule import GetSchedule
from src.use_cases.new_data import NewData
from src.use_cases.question import Question
from src.use_cases.remove_data import RemoveDataById
from src.use_cases.search_data import SearchDataById, SearchDataByListOfStr

sample_data = Data(id=1, source="example.com", content="Деканат находится в корпусе 2")


def _client_with_overrides(overrides: dict) -> TestClient:
    app = create_app()
    app.dependency_overrides.update(overrides)
    return TestClient(app)


def test_upload_page_serves_html() -> None:
    client = _client_with_overrides({})

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<form" in response.text


class _StubQuestion:
    """Use case-заглушка: API-тестам важна форма ответа, а не пайплайн (он покрыт в test_question)."""

    def __init__(self, result) -> None:
        self.result = result
        self.calls: list[tuple] = []

    async def execute(self, question, facts=None, history=None):
        self.calls.append((question, facts, history))
        return self.result


def test_ask_question_returns_answer_with_location_of_mentioned_building() -> None:
    client = _client_with_overrides({get_question_use_case: lambda: _StubQuestion(Answer(text="Деканат в корпусе 2."))})

    response = client.post("/question", json={"question": "Где деканат?"})

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Деканат в корпусе 2.",
        "clarification": None,
        "location": {"building": "2", "room": None, "floor": None},
        "route": None,
    }


def test_ask_question_returns_no_location_for_non_navigation_question() -> None:
    stub = _StubQuestion(Answer(text="Документы сдаются в корпусе 2."))
    client = _client_with_overrides({get_question_use_case: lambda: stub})

    response = client.post("/question", json={"question": "Какие есть стипендии?"})

    assert response.json()["location"] is None


async def test_ask_question_returns_route_instead_of_location() -> None:
    from src.repositories.json_campus_repository import JsonCampusRepository
    from src.services.campus_service import CampusService
    from src.use_cases.build_route import BuildRoute

    route = await BuildRoute(CampusService(JsonCampusRepository())).execute(None, "7-404")
    client = _client_with_overrides({get_question_use_case: lambda: _StubQuestion(Answer(text=route.text(), route=route))})

    body = client.post("/question", json={"question": "как пройти в 7-404"}).json()

    assert body["route"]["points"][-1]["floor"] == 4
    assert body["location"] is None


def test_ask_question_passes_chat_history_to_use_case() -> None:
    stub = _StubQuestion(Answer(text="Через главный вход."))
    client = _client_with_overrides({get_question_use_case: lambda: stub})

    client.post(
        "/question",
        json={"question": "а как туда пройти?", "history": [{"question": "где деканат", "answer": "В корпусе 2."}]},
    )

    _, _, history = stub.calls[0]
    assert history == [DialogTurn(question="где деканат", answer="В корпусе 2.")]


async def test_search_returns_matched_data(
    fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    await fake_vector_search_service.index(sample_data.id, [1.0])
    fake_data_store_service.store[sample_data.id] = sample_data
    use_case = SearchDataByListOfStr(fake_embedding_service, fake_vector_search_service, fake_data_store_service)

    client = _client_with_overrides({get_search_data_use_case: lambda: use_case})

    response = client.post("/search", json={"really_questions": ["где деканат"]})

    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "source": "example.com", "content": "Деканат находится в корпусе 2", "division": None}
    ]


def test_add_data_returns_generated_id(
    make_fake_llm_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    from src.use_cases.analyze_data import AnalyzeDataByLLMForNewData

    analyze_data = AnalyzeDataByLLMForNewData(make_fake_llm_service('["где деканат"]'))
    use_case = NewData(analyze_data, fake_embedding_service, fake_vector_search_service, fake_data_store_service)

    client = _client_with_overrides({get_new_data_use_case: lambda: use_case})

    response = client.post("/data", json={"source": "example.com", "content": "Деканат находится в корпусе 2"})

    assert response.status_code == 200
    assert response.json() == {"id": 1}


def test_add_data_returns_422_when_llm_generates_no_questions(
    make_fake_llm_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    from src.use_cases.analyze_data import AnalyzeDataByLLMForNewData

    analyze_data = AnalyzeDataByLLMForNewData(make_fake_llm_service("[]"))
    use_case = NewData(analyze_data, fake_embedding_service, fake_vector_search_service, fake_data_store_service)

    client = _client_with_overrides({get_new_data_use_case: lambda: use_case})

    response = client.post("/data", json={"source": "example.com", "content": "Деканат находится в корпусе 2"})

    assert response.status_code == 422


def test_add_data_rejects_unknown_division_slug(
    make_fake_llm_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    from src.use_cases.analyze_data import AnalyzeDataByLLMForNewData

    analyze_data = AnalyzeDataByLLMForNewData(make_fake_llm_service('["где деканат"]'))
    use_case = NewData(analyze_data, fake_embedding_service, fake_vector_search_service, fake_data_store_service)

    client = _client_with_overrides({get_new_data_use_case: lambda: use_case})

    response = client.post(
        "/data",
        json={
            "source": "example.com",
            "content": "Деканат находится в корпусе 2",
            "division": "not-a-real-division",
        },
    )

    assert response.status_code == 422


def test_get_data_returns_404_when_missing(fake_data_store_service) -> None:
    use_case = SearchDataById(fake_data_store_service)

    client = _client_with_overrides({get_search_data_by_id_use_case: lambda: use_case})

    response = client.get("/data/999")

    assert response.status_code == 404


def test_get_data_returns_data_when_found(fake_data_store_service) -> None:
    fake_data_store_service.store[sample_data.id] = sample_data
    use_case = SearchDataById(fake_data_store_service)

    client = _client_with_overrides({get_search_data_by_id_use_case: lambda: use_case})

    response = client.get("/data/1")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "source": "example.com",
        "content": "Деканат находится в корпусе 2",
        "division": None,
    }


async def test_delete_data_returns_ok_true(fake_data_store_service, fake_vector_search_service) -> None:
    fake_data_store_service.store[sample_data.id] = sample_data
    use_case = RemoveDataById(fake_data_store_service, fake_vector_search_service)

    client = _client_with_overrides({get_remove_data_use_case: lambda: use_case})

    response = client.delete("/data/1")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert await fake_data_store_service.get(1) is None


def test_ask_question_returns_clarification_when_student_info_missing() -> None:
    stub = _StubQuestion(ClarificationRequest(field="group", question="В какой группе вы учитесь?"))
    client = _client_with_overrides({get_question_use_case: lambda: stub})

    response = client.post("/question", json={"question": "Какое у меня завтра расписание?"})

    assert response.status_code == 200
    assert response.json() == {
        "answer": None,
        "clarification": {"field": "group", "question": "В какой группе вы учитесь?"},
        "location": None,
        "route": None,
    }


def test_ask_question_rejects_malformed_fact_field() -> None:
    # до use case дело дойти не должно - валидация отсекает запрос раньше
    client = _client_with_overrides({get_question_use_case: lambda: None})

    response = client.post(
        "/question", json={"question": "расписание", "facts": [{"field": "DROP TABLE", "value": "x"}]}
    )

    assert response.status_code == 422


def test_campus_endpoint_returns_campuses_with_generated_rooms() -> None:
    client = _client_with_overrides({})

    response = client.get("/campus")

    assert response.status_code == 200
    ugatu = next(campus for campus in response.json() if campus["id"] == "ugatu")
    assert any(building["id"] == "7" for building in ugatu["buildings"])
    assert ugatu["stairs"]
    assert any(room[0] == "404" and room[1] == 4 for room in ugatu["rooms"]["7"])


def test_route_endpoint_builds_route() -> None:
    client = _client_with_overrides({})

    response = client.post("/route", json={"source": "kpp", "target": "7-404"})

    assert response.status_code == 200
    body = response.json()
    assert body["campus"] == "ugatu"
    assert body["points"][-1]["floor"] == 4
    assert "7-404" in body["text"]


def test_route_endpoint_returns_404_for_unknown_place() -> None:
    client = _client_with_overrides({})

    response = client.post("/route", json={"source": "kpp", "target": "куда-то"})

    assert response.status_code == 404


def test_ask_question_returns_503_with_readable_message_when_llm_is_overloaded() -> None:
    from src.services.llm_service import LLMUnavailableError

    class _OverloadedQuestion:
        async def execute(self, question, facts=None, history=None):
            raise LLMUnavailableError("503 high demand")

    client = _client_with_overrides({get_question_use_case: lambda: _OverloadedQuestion()})

    response = client.post(
        "/question", json={"question": "где деканат"}, headers={"Origin": "http://localhost:3000"}
    )

    assert response.status_code == 503
    assert "перегружен" in response.json()["detail"]
    # CORS-заголовок на месте - браузер покажет сообщение, а не «ошибку CORS»
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_news_import_endpoint_reports_what_was_imported() -> None:
    from src.api.dependencies import get_import_news_use_case
    from src.domain.news import ImportReport

    class _StubImport:
        async def execute(self, limit: int) -> ImportReport:
            return ImportReport(imported=3, skipped=10, failed=1)

    client = _client_with_overrides({get_import_news_use_case: lambda: _StubImport()})

    response = client.post("/news/import?limit=14")

    assert response.status_code == 200
    assert response.json() == {"imported": 3, "skipped": 10, "failed": 1}
