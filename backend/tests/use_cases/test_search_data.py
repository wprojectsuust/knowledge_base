from src.domain.data import Data
from src.use_cases.search_data import SearchDataById, SearchDataByListOfStr


async def test_search_by_list_of_str_dedupes_ids_across_questions(
    sample_data, fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    await fake_vector_search_service.index(sample_data.id, [1.0])
    fake_data_store_service.store[sample_data.id] = sample_data
    use_case = SearchDataByListOfStr(fake_embedding_service, fake_vector_search_service, fake_data_store_service)

    result = await use_case.execute(["Где деканат?", "Где находится деканат?"])

    assert result == [sample_data]


async def test_search_by_list_of_str_returns_empty_when_no_questions(
    fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    use_case = SearchDataByListOfStr(fake_embedding_service, fake_vector_search_service, fake_data_store_service)

    assert await use_case.execute([]) == []


async def test_search_data_by_id_returns_existing(sample_data, fake_data_store_service) -> None:
    fake_data_store_service.store[sample_data.id] = sample_data
    use_case = SearchDataById(fake_data_store_service)

    assert await use_case.execute(sample_data.id) == sample_data


async def test_search_data_by_id_returns_none_when_missing(fake_data_store_service) -> None:
    use_case = SearchDataById(fake_data_store_service)

    assert await use_case.execute(999) is None


async def test_search_by_list_of_str_prioritizes_division_matches(
    fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    matched = Data(id=1, source="uust.ru", content="Расписание ИИМРТ", division="iimrt")
    other = Data(id=2, source="uust.ru", content="Расписание ФТИ", division="fti")
    await fake_vector_search_service.index(other.id, [1.0], division=other.division)
    await fake_vector_search_service.index(matched.id, [1.0], division=matched.division)
    fake_data_store_service.store[matched.id] = matched
    fake_data_store_service.store[other.id] = other

    use_case = SearchDataByListOfStr(fake_embedding_service, fake_vector_search_service, fake_data_store_service)

    result = await use_case.execute(["где иимрт"], division="iimrt")

    assert result[0] == matched
    assert other in result


async def test_search_by_list_of_str_drops_documents_below_similarity_threshold(
    fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    relevant = Data(id=1, source="uust.ru", content="Пропуски занятий отрабатываются через тьютора.")
    irrelevant = Data(id=2, source="uust.ru", content="Клуб настольных игр встречается по вторникам.")
    for item, score in ((relevant, 0.9), (irrelevant, 0.1)):
        await fake_vector_search_service.index(item.id, [1.0])
        fake_vector_search_service.scores[item.id] = score
        fake_data_store_service.store[item.id] = item
    use_case = SearchDataByListOfStr(fake_embedding_service, fake_vector_search_service, fake_data_store_service)

    result = await use_case.execute(["что делать, если пропустил пару"])

    assert result == [relevant]


async def test_document_lists_do_not_crowd_out_real_answers(
    fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    # порции «Официальные документы УУНиТ…» - длинные списки названий, похожи почти на любой
    # вопрос; без ограничения они занимали всю выдачу и вытесняли FAQ с настоящим ответом
    for id_ in range(1, 7):
        fake_data_store_service.store[id_] = Data(
            id=id_, source=f"https://uust.ru/sveden/document/#batch{id_}", content=f"Официальные документы, порция {id_}"
        )
        await fake_vector_search_service.index(id_, [1.0])
    fake_data_store_service.store[7] = Data(id=7, source="", content="Что делать, если не сдал экзамен: пересдача…")
    await fake_vector_search_service.index(7, [1.0])

    found = await SearchDataByListOfStr(
        fake_embedding_service, fake_vector_search_service, fake_data_store_service, n_results=6
    ).execute(["правила пересдачи"])

    assert 7 in [item.id for item in found]
    assert sum(item.source.startswith("https://uust.ru/sveden/document/") for item in found) == 2
