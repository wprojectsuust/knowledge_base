import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from src import config
from src.api.dependencies import (
    get_data_store_service,
    get_embedding_service,
    get_import_documents_use_case,
    get_import_news_use_case,
    get_llm_service,
    get_question_cache_service,
    get_schedule_cache_service,
    get_vector_search_service,
)
from src.api.routes import LLM_UNAVAILABLE_DETAIL, router
from src.services.llm_service import LLMUnavailableError

logger = logging.getLogger(__name__)


async def _import_news_periodically() -> None:
    """Фоновый импорт новостей uust.ru. Первый прогон - через минуту после старта (чтобы не
    мешать прогреву), дальше раз в NEWS_IMPORT_INTERVAL_MINUTES. Ошибка одного прогона не
    останавливает следующие."""
    await asyncio.sleep(60)
    while True:
        try:
            await get_import_news_use_case().execute(limit=config.NEWS_IMPORT_LIMIT)
        except Exception:
            logger.exception("Импорт новостей: прогон упал, попробую в следующий раз")
        await asyncio.sleep(config.NEWS_IMPORT_INTERVAL_MINUTES * 60)


async def _import_documents_periodically() -> None:
    """Фоновая синхронизация списка документов uust.ru/sveden/document/. Первый прогон - через
    5 минут после старта (после первого импорта новостей), дальше раз в DOCUMENTS_IMPORT_INTERVAL_HOURS."""
    await asyncio.sleep(5 * 60)
    while True:
        try:
            await get_import_documents_use_case().execute()
        except Exception:
            logger.exception("Импорт документов: прогон упал, попробую в следующий раз")
        await asyncio.sleep(config.DOCUMENTS_IMPORT_INTERVAL_HOURS * 3600)


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

    news_task = None
    if config.NEWS_IMPORT_INTERVAL_MINUTES > 0:
        news_task = asyncio.create_task(_import_news_periodically())
        logger.info("Импорт новостей uust.ru: раз в %d мин", config.NEWS_IMPORT_INTERVAL_MINUTES)

    documents_task = None
    if config.DOCUMENTS_IMPORT_INTERVAL_HOURS > 0:
        documents_task = asyncio.create_task(_import_documents_periodically())
        logger.info("Импорт документов uust.ru: раз в %d ч", config.DOCUMENTS_IMPORT_INTERVAL_HOURS)

    logger.info("Сервер готов принимать запросы")
    yield
    logger.info("Остановка сервера")
    for task in (news_task, documents_task):
        if task is not None:
            task.cancel()


def create_app() -> FastAPI:
    app = FastAPI(title="УУНиТ Knowledge Base", lifespan=lifespan)

    # "*" - любой источник (фронт открывают по IP машины, с телефона в той же сети и т.п.);
    # либо список адресов через запятую. Куки/авторизации нет, поэтому "*" безопасен.
    origins = [o.strip() for o in os.environ.get("FRONTEND_ORIGIN", "*").split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
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
            content={"detail": LLM_UNAVAILABLE_DETAIL},
        )

    app.include_router(router)
    return app


app = create_app()
