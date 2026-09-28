from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Protocol

from src import config
from src.logging_utils import preview

logger = logging.getLogger(__name__)


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


class LLMUnavailableError(Exception):
    """LLM не ответила даже после повторов (перегрузка 503, лимит 429, сеть, таймаут).
    API превращает её в 503 с понятным текстом - см. api/app.py."""


class LLMProvider(Protocol):
    """Абстракция над конкретным API-поставщиком LLM."""

    def generate(self, prompt: str) -> str:
        ...


class GeminiProvider:
    """Провайдер поверх Gemini через OpenAI-совместимый эндпоинт.

    model может быть списком через запятую: первая - основная, остальные - запасные на случай,
    когда основная перегружена (Gemini регулярно отвечает 503 "high demand" на бесплатном тарифе)."""

    def __init__(self, api_key: str, model: str, proxy_url: str | None = None) -> None:
        import httpx
        from openai import OpenAI

        http_client = httpx.Client(proxy=proxy_url, timeout=45.0) if proxy_url else httpx.Client(timeout=45.0)
        self._client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            http_client=http_client,
            # Gemini периодически отвечает 503 "high demand" - пики короткие, поэтому повторяем
            # чаще, чем по умолчанию (2), с экспоненциальной паузой внутри клиента openai
            max_retries=config.LLM_MAX_RETRIES,
        )
        self._models = [name.strip() for name in model.split(",") if name.strip()]
        logger.info(
            "GeminiProvider: инициализирован, модели=%s, прокси=%s", self._models, "да" if proxy_url else "нет"
        )

    def generate(self, prompt: str) -> str:
        last_error: Exception | None = None
        for model in self._models:
            logger.debug("Gemini запрос: model=%s prompt=%s", model, preview(prompt))
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    temperature=0.2,
                    messages=[{"role": "user", "content": prompt}],
                )
            except Exception as error:  # любая ошибка внешнего API для нас значит «модель недоступна»
                logger.warning("Gemini %s недоступна после повторов: %s", model, error)
                last_error = error
                continue
            answer = response.choices[0].message.content.strip()
            logger.debug("Gemini ответ (%s): %s", model, preview(answer))
            return answer
        raise LLMUnavailableError(str(last_error)) from last_error


class LLMService:
    """Обёртка над LLMProvider - позволяет быстро сменить провайдера/модель,
    не трогая юз-кейсы, которые от неё зависят.

    generate() асинхронный: GeminiProvider делает блокирующий сетевой вызов (openai/httpx
    синхронные), а это самая долгая операция во всём пайплайне - без to_thread один
    медленный запрос к LLM блокировал бы event loop и все остальные запросы к серверу.

    Плюс глобальный (на весь процесс) семафор ограничивает число одновременных запросов
    к LLM сверху (см. config.LLM_MAX_CONCURRENCY) - защита от перегрузки внешнего API
    и от слишком большого числа параллельных сетевых вызовов с одного инстанса."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider
        self._semaphore = asyncio.Semaphore(config.LLM_MAX_CONCURRENCY)

    async def generate(self, prompt: str) -> str:
        async with self._semaphore:
            return await asyncio.to_thread(self._provider.generate, prompt)

    @classmethod
    def from_env(cls) -> "LLMService":
        api_key = os.environ["GEMINI_API_KEY"]
        model = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash,gemini-2.5-flash,gemini-flash-latest,gemini-3.1-flash-lite")
        proxy = os.environ.get("PROXY_URL")
        return cls(GeminiProvider(api_key=api_key, model=model, proxy_url=proxy))
