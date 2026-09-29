import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from src import config

from src.domain.official_document import DOCUMENTS_PAGE_URL, document_batches
from src.services.data_store_service import DataStoreService
from src.services.llm_service import LLMUnavailableError
from src.services.official_documents_service import OfficialDocumentsService
from src.use_cases.new_data import NewData
from src.use_cases.remove_data import RemoveDataById

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class DocumentsImportReport:
    imported: int = 0
    skipped: int = 0  # порция не изменилась - уже в базе
    removed: int = 0  # устаревшие порции (документы изменились или пропали со страницы)
    failed: int = 0


class ImportDocuments:
    """Синхронизирует список официальных документов вуза (название + ссылка) с базой знаний:
    на «где найти положение о стипендии» бот отвечает ссылкой на документ.

    Список режется на порции (document_batches), source порции содержит хэш её текста. Новые
    порции проходят обычный NewData, неизменившиеся пропускаются без вызовов LLM. Устаревшие
    удаляются только когда все новые загрузились - иначе в базе на время была бы дыра."""

    def __init__(
        self,
        documents_service: OfficialDocumentsService,
        data_store_service: DataStoreService,
        new_data: NewData,
        remove_data: RemoveDataById,
        batch_size: int = config.DOCUMENTS_IMPORT_BATCH_SIZE,
        pause_seconds: float = config.NEWS_IMPORT_PAUSE_SECONDS,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._documents_service = documents_service
        self._data_store_service = data_store_service
        self._new_data = new_data
        self._remove_data = remove_data
        self._batch_size = batch_size
        # пауза между обращениями к LLM - импорт не должен выедать лимит запросов живых вопросов
        self._pause_seconds = pause_seconds
        self._sleep = sleep

    async def execute(self) -> DocumentsImportReport:
        documents = await self._documents_service.documents()
        if not documents:
            # сайт лежит или сменил вёрстку - базу не трогаем
            logger.warning("ImportDocuments: список документов пуст, пропускаю синхронизацию")
            return DocumentsImportReport()

        batches = document_batches(documents, size=self._batch_size)
        known = await self._data_store_service.sources_with_prefix(DOCUMENTS_PAGE_URL)
        imported = failed = 0
        asked_llm = False
        for batch in batches:
            if batch.source in known:
                continue
            if asked_llm:
                await self._sleep(self._pause_seconds)
            asked_llm = True
            try:
                new_id = await self._new_data.execute(batch)
            except LLMUnavailableError:
                logger.warning("ImportDocuments: LLM недоступна, остальное - в следующий раз")
                failed += 1
                break
            if new_id is None:
                failed += 1
            else:
                imported += 1

        removed = 0
        current = {batch.source for batch in batches}
        if not failed:
            for source, id_ in known.items():
                if source not in current:
                    await self._remove_data.execute(id_)
                    removed += 1

        report = DocumentsImportReport(
            imported=imported, skipped=len(current & known.keys()), removed=removed, failed=failed
        )
        logger.info("ImportDocuments: документов %d, порций %d, %s", len(documents), len(batches), report)
        return report
