"""E2E: гоняет запросы к реально запущенному серверу (весь стек: app + Postgres + Chroma
+ настоящий Gemini API). Ничего не мокается.

Требует: `make up` (или `docker compose up -d`) и валидный GEMINI_API_KEY в .env.
По умолчанию pytest эти тесты пропускает (см. addopts в pyproject.toml) - запуск
явный: `pytest -m e2e`. E2E_BASE_URL можно переопределить (по умолчанию localhost:8000).
"""

import os

import httpx
import pytest

pytestmark = pytest.mark.e2e

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")


@pytest.fixture
def client() -> httpx.Client:
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as http_client:
        yield http_client


def test_full_knowledge_base_workflow(client: httpx.Client) -> None:
    create_response = client.post(
        "/data",
        json={
            "source": "e2e-test",
            "content": "Клуб e2e-тестировщиков УУНиТ собирается по средам в 19:00 в аудитории 101.",
        },
    )
    assert create_response.status_code == 200
    new_id = create_response.json()["id"]

    try:
        get_response = client.get(f"/data/{new_id}")
        assert get_response.status_code == 200
        assert get_response.json()["content"].startswith("Клуб e2e-тестировщиков")

        question_response = client.post(
            "/question", json={"question": "Когда и где собирается клуб e2e-тестировщиков?"}
        )
        assert question_response.status_code == 200
        answer = question_response.json()["answer"]
        assert answer

        # Второй одинаковый вопрос должен прийти из кэша (быстрее, без нового обращения к LLM) -
        # здесь просто проверяем, что ответ идентичен, сам факт кэш-хита не наблюдаем снаружи.
        cached_response = client.post(
            "/question", json={"question": "Когда и где собирается клуб e2e-тестировщиков?"}
        )
        assert cached_response.status_code == 200
        assert cached_response.json()["answer"] == answer
    finally:
        delete_response = client.delete(f"/data/{new_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["ok"] is True

    missing_response = client.get(f"/data/{new_id}")
    assert missing_response.status_code == 404


def test_add_data_rejects_unknown_division(client: httpx.Client) -> None:
    response = client.post(
        "/data",
        json={"source": "e2e-test", "content": "Текст без смысла", "division": "not-a-real-division"},
    )
    assert response.status_code == 422
