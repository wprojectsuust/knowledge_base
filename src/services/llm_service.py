from __future__ import annotations

import json
import os
from typing import Protocol


def parse_string_list(raw: str) -> list[str]:
    """Разбирает ответ LLM, ожидаемый как JSON-массив строк, с запасным построчным парсингом,
    если модель не выдержала формат."""
    raw = raw.strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return [line.strip("- \t\n\"'") for line in raw.splitlines() if line.strip()]

    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    if isinstance(parsed, dict):
        for value in parsed.values():
            if isinstance(value, list):
                return [str(item).strip() for item in value if str(item).strip()]
    return []


class LLMProvider(Protocol):
    """Абстракция над конкретным API-поставщиком LLM."""

    def generate(self, prompt: str) -> str:
        ...


class GeminiProvider:
    """Провайдер поверх Gemini через OpenAI-совместимый эндпоинт."""

    def __init__(self, api_key: str, model: str, proxy_url: str | None = None) -> None:
        import httpx
        from openai import OpenAI

        http_client = httpx.Client(proxy=proxy_url, timeout=45.0) if proxy_url else httpx.Client(timeout=45.0)
        self._client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            http_client=http_client,
        )
        self._model = model

    def generate(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()


class LLMService:
    """Обёртка над LLMProvider - позволяет быстро сменить провайдера/модель,
    не трогая юз-кейсы, которые от неё зависят."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def generate(self, prompt: str) -> str:
        return self._provider.generate(prompt)

    @classmethod
    def from_env(cls) -> "LLMService":
        api_key = os.environ["GEMINI_API_KEY"]
        model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
        proxy = os.environ.get("PROXY_URL")
        return cls(GeminiProvider(api_key=api_key, model=model, proxy_url=proxy))
