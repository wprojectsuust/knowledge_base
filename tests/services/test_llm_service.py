from unittest.mock import MagicMock

from src.services.llm_service import GeminiProvider, LLMService, parse_string_list


def test_llm_service_delegates_to_provider() -> None:
    class FakeProvider:
        def __init__(self) -> None:
            self.last_prompt: str | None = None

        def generate(self, prompt: str) -> str:
            self.last_prompt = prompt
            return f"echo: {prompt}"

    provider = FakeProvider()
    service = LLMService(provider)

    result = service.generate("Где деканат?")

    assert result == "echo: Где деканат?"
    assert provider.last_prompt == "Где деканат?"


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
