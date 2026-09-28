import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from src.api.dependencies import (
    get_data_store_service,
    get_embedding_service,
    get_llm_service,
    get_question_cache_service,
    get_schedule_cache_service,
    get_vector_search_service,
)
from src.api.routes import router
from src.services.llm_service import LLMUnavailableError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск: прогреваем сервисы и подключения...")

    warmups = (
        ("LLM-сервис", get_llm_service),
        ("модель эмбеддингов", get_embedding_service),
        ("векторная БД (Chroma)", get_vector_search_service),
    )
    for name, factory in warmups:
        try:
            factory()
            logger.info("%s: готово", name)
        except Exception:
            logger.exception("%s: не удалось прогреть заранее, будет создано лениво при первом запросе", name)

    try:
        await get_data_store_service().connect()
        logger.info("PostgreSQL (документы): пул подключений готов")
    except Exception:
        logger.exception("PostgreSQL (документы): не удалось подключиться заранее, будет создано лениво при первом запросе")

    try:
        await get_question_cache_service().connect()
        logger.info("PostgreSQL (кэш вопросов): пул подключений готов")
    except Exception:
        logger.exception("PostgreSQL (кэш вопросов): не удалось подключиться заранее, будет создано лениво при первом запросе")

    try:
        await get_schedule_cache_service().connect()
        logger.info("PostgreSQL (кэш расписания): пул подключений готов")
    except Exception:
        logger.exception("PostgreSQL (кэш расписания): не удалось подключиться заранее, будет создано лениво при первом запросе")

    logger.info("Сервер готов принимать запросы")
    yield
    logger.info("Остановка сервера")


def create_app() -> FastAPI:
    app = FastAPI(title="УУНиТ Knowledge Base", lifespan=lifespan)

    frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_origin],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # /campus отдаёт раскладку всех кабинетов (~сотни КБ JSON) - сжимаем
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    # Обработчик срабатывает внутри CORS-мидлвари: ответ уходит с CORS-заголовками, и фронт
    # показывает понятное сообщение, а не «заблокировано политикой CORS» на голом 500.
    @app.exception_handler(LLMUnavailableError)
    async def llm_unavailable(_: Request, error: LLMUnavailableError) -> JSONResponse:
        logger.warning("LLM недоступна, отвечаю 503: %s", error)
        return JSONResponse(
            status_code=503,
            content={"detail": "ИИ-модель сейчас перегружена, попробуйте ещё раз через минуту."},
        )

    app.include_router(router)
    return app


app = create_app()
