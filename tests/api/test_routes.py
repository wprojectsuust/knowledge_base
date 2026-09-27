from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.dependencies import (
    get_new_data_use_case,
    get_question_use_case,
    get_remove_data_use_case,
    get_search_data_by_id_use_case,
    get_search_data_use_case,
)
from src.domain.data import Data
from src.use_cases.analyze_data import AnalyzeDataByLLMForUser
from src.use_cases.get_really_questions import GetReallyQuestions
from src.use_cases.new_data import NewData
from src.use_cases.question import Question
from src.use_cases.remove_data import RemoveDataById
from src.use_cases.search_data import SearchDataById, SearchDataByListOfStr

sample_data = Data(id=1, source="example.com", content="Деканат находится в корпусе 2")


def _client_with_overrides(overrides: dict) -> TestClient:
    app = create_app()
    app.dependency_overrides.update(overrides)
    return TestClient(app)


def test_ask_question_returns_answer_from_use_case(
    make_fake_llm_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    fake_vector_search_service.index(sample_data.id, [1.0])
    fake_data_store_service.store[sample_data.id] = sample_data

    get_really_questions = GetReallyQuestions(make_fake_llm_service('["где деканат"]'))
    search_data = SearchDataByListOfStr(fake_embedding_service, fake_vector_search_service, fake_data_store_service)
    analyze_data = AnalyzeDataByLLMForUser(make_fake_llm_service("Деканат в корпусе 2."))
    use_case = Question(get_really_questions, search_data, analyze_data)

    client = _client_with_overrides({get_question_use_case: lambda: use_case})

    response = client.post("/question", json={"question": "Где деканат?"})

    assert response.status_code == 200
    assert response.json() == {"answer": "Деканат в корпусе 2."}


def test_search_returns_matched_data(fake_embedding_service, fake_vector_search_service, fake_data_store_service) -> None:
    fake_vector_search_service.index(sample_data.id, [1.0])
    fake_data_store_service.store[sample_data.id] = sample_data
    use_case = SearchDataByListOfStr(fake_embedding_service, fake_vector_search_service, fake_data_store_service)

    client = _client_with_overrides({get_search_data_use_case: lambda: use_case})

    response = client.post("/search", json={"really_questions": ["где деканат"]})

    assert response.status_code == 200
    assert response.json() == [{"id": 1, "source": "example.com", "content": "Деканат находится в корпусе 2"}]


def test_add_data_returns_ok_true(
    make_fake_llm_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    from src.use_cases.analyze_data import AnalyzeDataByLLMForNewData

    analyze_data = AnalyzeDataByLLMForNewData(make_fake_llm_service('["где деканат"]'))
    use_case = NewData(analyze_data, fake_embedding_service, fake_vector_search_service, fake_data_store_service)

    client = _client_with_overrides({get_new_data_use_case: lambda: use_case})

    response = client.post("/data", json={"id": 1, "source": "example.com", "content": "Деканат находится в корпусе 2"})

    assert response.status_code == 200
    assert response.json() == {"ok": True}


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
    assert response.json() == {"id": 1, "source": "example.com", "content": "Деканат находится в корпусе 2"}


async def test_delete_data_returns_ok_true(fake_data_store_service, fake_vector_search_service) -> None:
    fake_data_store_service.store[sample_data.id] = sample_data
    use_case = RemoveDataById(fake_data_store_service, fake_vector_search_service)

    client = _client_with_overrides({get_remove_data_use_case: lambda: use_case})

    response = client.delete("/data/1")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert await fake_data_store_service.get(1) is None
