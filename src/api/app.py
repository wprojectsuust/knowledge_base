import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.dependencies import (
    get_data_store_service,
    get_embedding_service,
    get_llm_service,
    get_question_cache_service,
    get_vector_search_service,
)
from src.api.routes import router

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

    logger.info("Сервер готов принимать запросы")
    yield
    logger.info("Остановка сервера")


def create_app() -> FastAPI:
    app = FastAPI(title="УУНиТ Knowledge Base", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
