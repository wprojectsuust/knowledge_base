from src.use_cases.search_data import SearchDataById, SearchDataByListOfStr


def test_search_by_list_of_str_dedupes_ids_across_questions(
    sample_data, fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    fake_vector_search_service.index(sample_data.id, [1.0])
    fake_data_store_service.store[sample_data.id] = sample_data
    use_case = SearchDataByListOfStr(fake_embedding_service, fake_vector_search_service, fake_data_store_service)

    result = use_case.execute(["Где деканат?", "Где находится деканат?"])

    assert result == [sample_data]


def test_search_by_list_of_str_returns_empty_when_no_questions(
    fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    use_case = SearchDataByListOfStr(fake_embedding_service, fake_vector_search_service, fake_data_store_service)

    assert use_case.execute([]) == []


def test_search_data_by_id_returns_existing(sample_data, fake_data_store_service) -> None:
    fake_data_store_service.store[sample_data.id] = sample_data
    use_case = SearchDataById(fake_data_store_service)

    assert use_case.execute(sample_data.id) == sample_data


def test_search_data_by_id_returns_none_when_missing(fake_data_store_service) -> None:
    use_case = SearchDataById(fake_data_store_service)

    assert use_case.execute(999) is None
