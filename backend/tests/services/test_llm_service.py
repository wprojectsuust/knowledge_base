import asyncio
import time
from unittest.mock import MagicMock

import pytest

import src.config as config
from src.services.llm_service import GeminiProvider, LLMService, parse_string_list


async def test_llm_service_delegates_to_provider() -> None:
    class FakeProvider:
        def __init__(self) -> None:
            self.last_prompt: str | None = None

        def generate(self, prompt: str) -> str:
            self.last_prompt = prompt
            return f"echo: {prompt}"

    provider = FakeProvider()
    service = LLMService(provider)

    result = await service.generate("Где деканат?")

    assert result == "echo: Где деканат?"
    assert provider.last_prompt == "Где деканат?"


async def test_llm_service_limits_concurrent_calls(monkeypatch) -> None:
    monkeypatch.setattr(config, "LLM_MAX_CONCURRENCY", 2)

    active = 0
    max_active = 0

    class SlowProvider:
        def generate(self, prompt: str) -> str:
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            time.sleep(0.05)
            active -= 1
            return "ok"

    service = LLMService(SlowProvider())

    await asyncio.gather(*(service.generate("x") for _ in range(6)))

    assert max_active <= 2


def test_gemini_provider_generate_returns_stripped_content(fake_openai: MagicMock) -> None:
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content="  ответ с пробелами  "))]
    fake_openai.return_value = fake_response

    provider = GeminiProvider(api_key="key", model="test-model")
    result = provider.generate("вопрос")

    assert result == "ответ с пробелами"
    _, kwargs = fake_openai.call_args
    assert kwargs["model"] == "test-model"
    assert kwargs["messages"] == [{"role": "user", "content": "вопрос"}]


def test_parse_string_list_from_json_array() -> None:
    assert parse_string_list('["a", "b"]') == ["a", "b"]


def test_parse_string_list_from_json_object_with_list_value() -> None:
    assert parse_string_list('{"questions": ["a", "b"]}') == ["a", "b"]


def test_parse_string_list_falls_back_to_line_split_on_invalid_json() -> None:
    raw = "- где деканат\n- как найти деканат"

    assert parse_string_list(raw) == ["где деканат", "как найти деканат"]


def test_parse_string_list_returns_empty_for_blank_input() -> None:
    assert parse_string_list("") == []


def test_parse_string_list_returns_empty_for_json_object_without_list() -> None:
    assert parse_string_list('{"note": "нет вопросов"}') == []


def test_gemini_provider_wraps_api_failure_into_llm_unavailable(fake_openai: MagicMock, clock) -> None:
    import pytest

    from src.services.llm_service import LLMUnavailableError

    fake_openai.side_effect = RuntimeError("Error code: 503 - model is currently experiencing high demand")

    provider = GeminiProvider(api_key="key", model="test-model")

    with pytest.raises(LLMUnavailableError):
        provider.generate("вопрос")


def test_gemini_provider_falls_back_to_next_model_when_first_is_overloaded(fake_openai: MagicMock, clock) -> None:
    ok = MagicMock()
    ok.choices = [MagicMock(message=MagicMock(content="ответ"))]

    def create(**kwargs):
        if kwargs["model"] == "busy-model":
            raise RuntimeError("503 high demand")
        return ok

    fake_openai.side_effect = create

    provider = GeminiProvider(api_key="key", model="busy-model, free-model")

    assert provider.generate("вопрос") == "ответ"
    # перегрузку (не 429) сначала повторяем - пики короткие, потом переходим на запасную
    assert [call.kwargs["model"] for call in fake_openai.call_args_list] == ["busy-model"] * (
        1 + config.LLM_MAX_RETRIES
    ) + ["free-model"]


class _StatusError(Exception):
    """Как openai.APIStatusError: ошибка с HTTP-статусом."""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"Error code: {status_code}")
        self.status_code = status_code


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock(monkeypatch) -> _Clock:
    from src.services import llm_service

    fake = _Clock()
    monkeypatch.setattr(llm_service.time, "monotonic", fake)
    monkeypatch.setattr(llm_service.time, "sleep", lambda seconds: setattr(fake, "now", fake.now + seconds))
    return fake


def _ok(text: str = "ответ") -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=text))]
    return response


def _models_called(fake_openai: MagicMock) -> list[str]:
    return [call.kwargs["model"] for call in fake_openai.call_args_list]


def test_rate_limited_model_is_not_retried_and_is_skipped_while_cooling_down(fake_openai: MagicMock, clock) -> None:
    fake_openai.side_effect = lambda **kwargs: (_ for _ in ()).throw(_StatusError(429)) if kwargs["model"] == "a" else _ok()
    provider = GeminiProvider(api_key="key", model="a, b")

    assert provider.generate("первый") == "ответ"
    assert provider.generate("второй") == "ответ"

    # 429 - сразу на запасную модель, без повторов; во второй раз в «a» даже не стучимся
    assert _models_called(fake_openai) == ["a", "b", "b"]


def test_rate_limited_model_is_used_again_after_cooldown(fake_openai: MagicMock, clock) -> None:
    from src import config

    calls = {"a": 0}

    def create(**kwargs):
        if kwargs["model"] == "a":
            calls["a"] += 1
            if calls["a"] == 1:
                raise _StatusError(429)
        return _ok()

    fake_openai.side_effect = create
    provider = GeminiProvider(api_key="key", model="a, b")

    provider.generate("первый")
    clock.now += config.LLM_RATE_LIMIT_COOLDOWN_SECONDS + 1
    provider.generate("второй")

    assert _models_called(fake_openai) == ["a", "b", "a"]


def test_fails_fast_without_requests_when_every_model_is_cooling_down(fake_openai: MagicMock, clock) -> None:
    from src.services.llm_service import LLMUnavailableError

    fake_openai.side_effect = _StatusError(429)
    provider = GeminiProvider(api_key="key", model="a, b")

    with pytest.raises(LLMUnavailableError):
        provider.generate("первый")
    with pytest.raises(LLMUnavailableError):
        provider.generate("второй")

    assert _models_called(fake_openai) == ["a", "b"]  # второй вызов не сделал ни одного запроса


def test_overloaded_model_is_retried_before_falling_back(fake_openai: MagicMock, clock) -> None:
    from src import config

    fake_openai.side_effect = lambda **kwargs: (_ for _ in ()).throw(_StatusError(503)) if kwargs["model"] == "a" else _ok()
    provider = GeminiProvider(api_key="key", model="a, b")

    provider.generate("вопрос")

    assert _models_called(fake_openai) == ["a"] * (1 + config.LLM_MAX_RETRIES) + ["b"]


def test_stops_trying_models_when_time_budget_is_spent(fake_openai: MagicMock, clock) -> None:
    from src import config
    from src.services.llm_service import LLMUnavailableError

    def slow_failure(**kwargs):
        clock.now += config.LLM_TOTAL_BUDGET_SECONDS + 1
        raise _StatusError(504)

    fake_openai.side_effect = slow_failure
    provider = GeminiProvider(api_key="key", model="slow-model, other-model, third-model")

    with pytest.raises(LLMUnavailableError):
        provider.generate("вопрос")
    # после первой попытки бюджет исчерпан - ни повторов, ни запасных моделей, студент не ждёт минутами
    assert _models_called(fake_openai) == ["slow-model"]
