import asyncio
import time
from unittest.mock import MagicMock

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


def test_gemini_provider_wraps_api_failure_into_llm_unavailable(fake_openai: MagicMock) -> None:
    import pytest

    from src.services.llm_service import LLMUnavailableError

    fake_openai.side_effect = RuntimeError("Error code: 503 - model is currently experiencing high demand")

    provider = GeminiProvider(api_key="key", model="test-model")

    with pytest.raises(LLMUnavailableError):
        provider.generate("вопрос")


def test_gemini_provider_falls_back_to_next_model_when_first_is_overloaded(fake_openai: MagicMock) -> None:
    ok = MagicMock()
    ok.choices = [MagicMock(message=MagicMock(content="ответ"))]

    def create(**kwargs):
        if kwargs["model"] == "busy-model":
            raise RuntimeError("503 high demand")
        return ok

    fake_openai.side_effect = create

    provider = GeminiProvider(api_key="key", model="busy-model, free-model")

    assert provider.generate("вопрос") == "ответ"
    assert [call.kwargs["model"] for call in fake_openai.call_args_list] == ["busy-model", "free-model"]
