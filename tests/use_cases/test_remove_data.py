from src.use_cases.remove_data import RemoveDataById


async def test_remove_data_by_id_clears_both_stores(
    sample_data, fake_data_store_service, fake_vector_search_service
) -> None:
    fake_data_store_service.store[sample_data.id] = sample_data
    await fake_vector_search_service.index(sample_data.id, [1.0])
    use_case = RemoveDataById(fake_data_store_service, fake_vector_search_service)

    assert await use_case.execute(sample_data.id) is True
    assert await fake_data_store_service.get(sample_data.id) is None
    assert sample_data.id not in fake_vector_search_service.index_calls
