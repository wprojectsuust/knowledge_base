import pytest

from src.domain.data import Data
from src.domain.official_document import OfficialDocument, document_batches
from src.use_cases.analyze_data import AnalyzeDataByLLMForNewData
from src.use_cases.import_documents import ImportDocuments
from src.use_cases.new_data import NewData
from src.use_cases.remove_data import RemoveDataById

RULES = OfficialDocument(title="Правила внутреннего распорядка", url="https://uust.ru/media/pvro.pdf", section="Локальные акты")
GRANTS = OfficialDocument(title="Положение о стипендиях", url="https://uust.ru/media/grants.pdf", section="Локальные акты")
FORM = OfficialDocument(title="Заявление на матпомощь", url="https://uust.ru/media/form.docx", section="Шаблоны документов")


class FakeDocumentsService:
    def __init__(self, documents) -> None:
        self._documents = documents

    async def documents(self) -> list[OfficialDocument]:
        return self._documents


async def _no_sleep(seconds: float) -> None:
    return None


@pytest.fixture
def make_import(fake_llm_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service):
    def _make(documents) -> ImportDocuments:
        fake_llm_service.response = '["где найти правила внутреннего распорядка"]'
        new_data = NewData(
            AnalyzeDataByLLMForNewData(fake_llm_service),
            fake_embedding_service,
            fake_vector_search_service,
            fake_data_store_service,
        )
        remove_data = RemoveDataById(fake_data_store_service, fake_vector_search_service)
        return ImportDocuments(
            FakeDocumentsService(documents), fake_data_store_service, new_data, remove_data,
            batch_size=10, pause_seconds=0, sleep=_no_sleep,
        )

    return _make


async def test_first_run_imports_every_batch(make_import, fake_data_store_service) -> None:
    report = await make_import([RULES, GRANTS, FORM]).execute()

    assert report.imported == 2  # два раздела - две записи
    contents = [item.content for item in fake_data_store_service.store.values()]
    assert any("Положение о стипендиях: https://uust.ru/media/grants.pdf" in text for text in contents)


async def test_unchanged_batches_are_skipped_and_outdated_ones_replaced(
    make_import, fake_data_store_service, fake_llm_service
) -> None:
    await make_import([RULES, FORM]).execute()
    calls_before = fake_llm_service.call_count

    report = await make_import([RULES, GRANTS, FORM]).execute()

    assert report.imported == 1 and report.skipped == 1 and report.removed == 1
    assert fake_llm_service.call_count == calls_before + 1  # LLM - только для изменившейся порции
    sources = {item.source for item in fake_data_store_service.store.values()}
    assert sources == {batch.source for batch in document_batches([RULES, GRANTS, FORM], size=10)}


async def test_empty_page_does_not_wipe_knowledge_base(make_import, fake_data_store_service) -> None:
    await make_import([RULES]).execute()

    report = await make_import([]).execute()

    assert report.removed == 0
    assert len(fake_data_store_service.store) == 1


async def test_keeps_outdated_batches_when_some_new_ones_failed(
    make_import, fake_data_store_service, fake_llm_service
) -> None:
    await make_import([RULES]).execute()
    importer = make_import([RULES, GRANTS])
    fake_llm_service.response = "[]"  # LLM не сгенерировала вопросов - порция не загружена

    report = await importer.execute()

    assert report.failed == 1 and report.removed == 0
    assert any(item.source.startswith("https://uust.ru/sveden/document/") for item in fake_data_store_service.store.values())


async def test_does_not_touch_other_records(make_import, fake_data_store_service) -> None:
    fake_data_store_service.store[1] = Data(id=1, source="https://uust.ru/news/get/x", content="новость")
    fake_data_store_service._next_id = 2

    await make_import([RULES]).execute()
    await make_import([GRANTS]).execute()

    assert fake_data_store_service.store[1].content == "новость"
