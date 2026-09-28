import datetime as dt
import logging

from src.domain.data import Data
from src.domain.news import ImportReport, NewsHeadline
from src.services.data_store_service import DataStoreService
from src.services.news_service import NewsService
from src.services.llm_service import LLMUnavailableError
from src.use_cases.new_data import NewData

logger = logging.getLogger(__name__)

MAX_ARTICLE_CHARS = 6000  # длинные лонгриды режем - в контекст ответа всё равно идёт суть


class ImportNews:
    """Подтягивает свежие новости с сайта в базу знаний. Уже загруженные (их ссылка - source
    документа) пропускаются и даже не скачиваются. Каждая новая новость проходит обычный
    NewData: LLM генерирует вопросы, они индексируются - и на «что нового»/«какие мероприятия»
    бот отвечает по новостям со ссылкой на них."""

    def __init__(self, news_service: NewsService, data_store_service: DataStoreService, new_data: NewData) -> None:
        self._news_service = news_service
        self._data_store_service = data_store_service
        self._new_data = new_data

    async def execute(self, limit: int) -> ImportReport:
        headlines = await self._news_service.latest(limit)
        known = await self._data_store_service.existing_sources([item.url for item in headlines])
        imported = failed = 0
        for headline in headlines:
            if headline.url in known:
                continue
            text = await self._news_service.article_text(headline.url)
            if not text:
                logger.warning("ImportNews: не удалось получить текст %s", headline.url)
                failed += 1
                continue
            try:
                new_id = await self._new_data.execute(Data(source=headline.url, content=self._content(headline, text)))
            except LLMUnavailableError:
                # LLM перегружена - остальное подтянем в следующий раз, эта новость не помечена загруженной
                logger.warning("ImportNews: LLM недоступна, прерываю импорт")
                failed += 1
                break
            if new_id is None:
                failed += 1
            else:
                imported += 1
        report = ImportReport(imported=imported, skipped=len(known), failed=failed)
        logger.info("ImportNews: %s", report)
        return report

    @staticmethod
    def _content(headline: NewsHeadline, text: str) -> str:
        try:
            day = dt.datetime.fromisoformat(headline.published_at).strftime("%d.%m.%Y")
        except ValueError:
            day = "неизвестной даты"
        body = text if len(text) <= MAX_ARTICLE_CHARS else text[:MAX_ARTICLE_CHARS] + "…"
        # дата и заголовок - прямо в тексте: иначе LLM не отличит прошедшее мероприятие от будущего
        return f"Новость УУНиТ от {day}: {headline.title}\n\n{body}"
