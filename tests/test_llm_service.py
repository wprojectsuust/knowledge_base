from src.services.llm_service import LLMService


class FakeProvider:
    def __init__(self) -> None:
        self.last_prompt: str | None = None

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return f"echo: {prompt}"


def test_llm_service_delegates_to_provider() -> None:
    provider = FakeProvider()
    service = LLMService(provider)

    result = service.generate("Где деканат?")

    assert result == "echo: Где деканат?"
    assert provider.last_prompt == "Где деканат?"
