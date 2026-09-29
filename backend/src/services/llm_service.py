from __future__ import annotations

import asyncio
import json
import logging
import os
import time
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


GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_GEMINI_MODELS = "gemini-3.6-flash,gemini-2.5-flash,gemini-flash-latest,gemini-3.1-flash-lite"


class OpenAICompatibleProvider:
    """Провайдер поверх любого OpenAI-совместимого API (Gemini, claudehub/Qwen и т.п.) - адрес,
    ключ и модели задаются в .env (LLM_BASE_URL, LLM_API_KEY, LLM_MODEL).

    model может быть списком через запятую: первая - основная, остальные - запасные.
    Бесплатный тариф Gemini то перегружен (503), то упирается в лимит запросов (429), поэтому:
    - 5xx и таймауты повторяем с нарастающей паузой (пики короткие);
    - на 429 НЕ повторяем: модель уходит «остыть» на LLM_RATE_LIMIT_COOLDOWN_SECONDS, и пока
      она остывает, запросы сразу идут на запасную - не долбим исчерпанный лимит;
    - всё это укладывается в общий бюджет времени LLM_TOTAL_BUDGET_SECONDS."""

    def __init__(self, api_key: str, model: str, proxy_url: str | None = None, base_url: str = GEMINI_BASE_URL) -> None:
        import httpx
        from openai import OpenAI

        timeout = config.LLM_TIMEOUT_SECONDS
        http_client = httpx.Client(proxy=proxy_url, timeout=timeout) if proxy_url else httpx.Client(timeout=timeout)
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=http_client,
            # повторы - свои (см. generate): встроенные в openai повторяют и 429, а это только
            # сжигает лимит и множит запросы
            max_retries=0,
        )
        self._models = [name.strip() for name in model.split(",") if name.strip()]
        self._cooling_until: dict[str, float] = {}
        logger.info(
            "LLM: инициализирован, адрес=%s, модели=%s, прокси=%s", base_url, self._models, "да" if proxy_url else "нет"
        )

    def generate(self, prompt: str) -> str:
        last_error: Exception | None = None
        started = time.monotonic()

        def budget_left() -> bool:
            return time.monotonic() - started <= config.LLM_TOTAL_BUDGET_SECONDS

        for model in self._models:
            if self._cooling_until.get(model, 0) > time.monotonic():
                logger.debug("LLM %s остывает после 429, пропускаю", model)
                continue
            # бюджет ограничивает только повторы и запасные модели - первую попытку делаем всегда
            if last_error is not None and not budget_left():
                logger.warning("LLM: бюджет %.0f с исчерпан, запасные модели не пробую", config.LLM_TOTAL_BUDGET_SECONDS)
                break
            for attempt in range(1 + config.LLM_MAX_RETRIES):
                logger.debug("LLM запрос: model=%s попытка=%d prompt=%s", model, attempt + 1, preview(prompt))
                try:
                    response = self._client.chat.completions.create(
                        model=model,
                        temperature=0.2,
                        messages=[{"role": "user", "content": prompt}],
                    )
                except Exception as error:  # любая ошибка внешнего API для нас значит «модель недоступна»
                    last_error = error
                    if getattr(error, "status_code", None) == 429:
                        self._cooling_until[model] = time.monotonic() + config.LLM_RATE_LIMIT_COOLDOWN_SECONDS
                        logger.warning(
                            "LLM %s: лимит запросов (429), остывает %d с", model, config.LLM_RATE_LIMIT_COOLDOWN_SECONDS
                        )
                        break
                    if attempt < config.LLM_MAX_RETRIES and budget_left():
                        pause = 2**attempt
                        logger.warning("LLM %s недоступна (%s), повтор через %d с", model, error, pause)
                        time.sleep(pause)
                        continue
                    logger.warning("LLM %s недоступна: %s", model, error)
                    break
                answer = response.choices[0].message.content.strip()
                logger.debug("LLM ответ (%s): %s", model, preview(answer))
                return answer
        if last_error is None:
            raise LLMUnavailableError("все модели упёрлись в лимит запросов и ещё остывают")
        raise LLMUnavailableError(str(last_error)) from last_error


class LLMService:
    """Обёртка над LLMProvider - позволяет быстро сменить провайдера/модель,
    не трогая юз-кейсы, которые от неё зависят.

    generate() асинхронный: провайдер делает блокирующий сетевой вызов (openai/httpx
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
        # LLM_* - основные настройки; GEMINI_* оставлены для совместимости со старыми .env
        # LLM_* применяются только вместе с ключом - иначе целиком Gemini, чтобы ключ Gemini
        # не ушёл на чужой адрес
        if os.environ.get("LLM_API_KEY"):
            api_key = os.environ["LLM_API_KEY"]
            model = os.environ.get("LLM_MODEL") or DEFAULT_GEMINI_MODELS
            base_url = os.environ.get("LLM_BASE_URL") or GEMINI_BASE_URL
        else:
            api_key = os.environ["GEMINI_API_KEY"]
            model = os.environ.get("GEMINI_MODEL") or DEFAULT_GEMINI_MODELS
            base_url = GEMINI_BASE_URL
        proxy = os.environ.get("PROXY_URL") or None
        return cls(OpenAICompatibleProvider(api_key=api_key, model=model, proxy_url=proxy, base_url=base_url))
