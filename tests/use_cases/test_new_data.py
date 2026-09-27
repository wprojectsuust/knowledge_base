from src.use_cases.analyze_data import AnalyzeDataByLLMForNewData
from src.use_cases.new_data import NewData


def test_new_data_saves_and_indexes_when_questions_generated(
    sample_data, fake_llm_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    fake_llm_service.response = '["где деканат"]'
    analyze_data = AnalyzeDataByLLMForNewData(fake_llm_service)
    use_case = NewData(analyze_data, fake_embedding_service, fake_vector_search_service, fake_data_store_service)

    assert use_case.execute(sample_data) is True
    assert fake_data_store_service.get(sample_data.id) == sample_data
    assert sample_data.id in fake_vector_search_service.index_calls


def test_new_data_returns_false_when_no_questions_generated(
    sample_data, fake_llm_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    fake_llm_service.response = "[]"
    analyze_data = AnalyzeDataByLLMForNewData(fake_llm_service)
    use_case = NewData(analyze_data, fake_embedding_service, fake_vector_search_service, fake_data_store_service)

    assert use_case.execute(sample_data) is False
    assert fake_data_store_service.get(sample_data.id) is None
