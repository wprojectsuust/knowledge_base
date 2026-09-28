from src.domain.data import Data
from src.use_cases.analyze_data import AnalyzeDataByLLMForNewData
from src.use_cases.new_data import NewData

new_document = Data(source="example.com", content="Деканат находится в корпусе 2")


async def test_new_data_saves_and_indexes_when_questions_generated(
    fake_llm_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    fake_llm_service.response = '["где деканат"]'
    analyze_data = AnalyzeDataByLLMForNewData(fake_llm_service)
    use_case = NewData(analyze_data, fake_embedding_service, fake_vector_search_service, fake_data_store_service)

    new_id = await use_case.execute(new_document)

    assert new_id is not None
    saved = await fake_data_store_service.get(new_id)
    assert saved == Data(id=new_id, source=new_document.source, content=new_document.content)
    assert new_id in fake_vector_search_service.index_calls


async def test_new_data_returns_none_when_no_questions_generated(
    fake_llm_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    fake_llm_service.response = "[]"
    analyze_data = AnalyzeDataByLLMForNewData(fake_llm_service)
    use_case = NewData(analyze_data, fake_embedding_service, fake_vector_search_service, fake_data_store_service)

    assert await use_case.execute(new_document) is None
    assert fake_data_store_service.store == {}


async def test_new_data_passes_division_to_vector_index(
    fake_llm_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    fake_llm_service.response = '["где деканат"]'
    document_with_division = Data(source="uust.ru", content="Расписание ИИМРТ", division="iimrt")
    analyze_data = AnalyzeDataByLLMForNewData(fake_llm_service)
    use_case = NewData(analyze_data, fake_embedding_service, fake_vector_search_service, fake_data_store_service)

    new_id = await use_case.execute(document_with_division)

    assert fake_vector_search_service.divisions[new_id] == "iimrt"


async def test_new_data_invalidates_question_cache(
    sample_data, fake_llm_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service, fake_question_cache_service
) -> None:
    # иначе закэшированное «в базе этого нет» переживёт загрузку нужного документа
    fake_question_cache_service.store["где деканат"] = "В базе этого нет."
    fake_llm_service.response = '["где деканат"]'
    use_case = NewData(
        AnalyzeDataByLLMForNewData(fake_llm_service),
        fake_embedding_service,
        fake_vector_search_service,
        fake_data_store_service,
        question_cache_service=fake_question_cache_service,
    )

    await use_case.execute(sample_data)

    assert fake_question_cache_service.store == {}
