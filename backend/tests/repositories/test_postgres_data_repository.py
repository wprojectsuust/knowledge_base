from src.domain.data import Data
from src.repositories.postgres_data_repository import PostgresDataRepository


def _make_repo() -> PostgresDataRepository:
    return PostgresDataRepository(dsn="postgresql://uunit:uunit@localhost:5432/uunit")


async def test_creates_documents_table_on_first_use(fake_asyncpg_pool) -> None:
    repo = _make_repo()

    await repo.get(1)

    create_table_call = fake_asyncpg_pool.execute.call_args_list[0]
    assert "CREATE TABLE IF NOT EXISTS documents" in create_table_call.args[0]


async def test_adds_division_column_for_tables_created_before_it_existed(fake_asyncpg_pool) -> None:
    repo = _make_repo()

    await repo.get(1)

    alter_column_call = fake_asyncpg_pool.execute.call_args_list[1]
    assert "ALTER TABLE documents ADD COLUMN IF NOT EXISTS division" in alter_column_call.args[0]


async def test_pool_is_created_only_once(fake_asyncpg_pool) -> None:
    repo = _make_repo()

    await repo.get(1)
    await repo.get(2)

    assert fake_asyncpg_pool.fetchrow.call_count == 2


async def test_get_returns_data_when_row_exists(sample_data, fake_asyncpg_pool) -> None:
    fake_asyncpg_pool.fetchrow.return_value = {
        "id": sample_data.id,
        "source": sample_data.source,
        "content": sample_data.content,
        "division": sample_data.division,
    }
    repo = _make_repo()

    result = await repo.get(sample_data.id)

    assert result == sample_data
    args, _ = fake_asyncpg_pool.fetchrow.call_args
    assert "WHERE id = $1" in args[0]
    assert args[1] == sample_data.id


async def test_get_returns_none_when_row_missing(fake_asyncpg_pool) -> None:
    fake_asyncpg_pool.fetchrow.return_value = None
    repo = _make_repo()

    assert await repo.get(999) is None


async def test_get_many_returns_empty_list_without_querying(fake_asyncpg_pool) -> None:
    repo = _make_repo()

    result = await repo.get_many([])

    assert result == []
    fake_asyncpg_pool.fetch.assert_not_called()


async def test_get_many_maps_rows_to_data(sample_data, fake_asyncpg_pool) -> None:
    fake_asyncpg_pool.fetch.return_value = [
        {
            "id": sample_data.id,
            "source": sample_data.source,
            "content": sample_data.content,
            "division": sample_data.division,
        },
    ]
    repo = _make_repo()

    result = await repo.get_many([sample_data.id, 999])

    assert result == [sample_data]
    args, _ = fake_asyncpg_pool.fetch.call_args
    assert args[1] == [sample_data.id, 999]


async def test_save_inserts_new_document_and_returns_generated_id(fake_asyncpg_pool) -> None:
    fake_asyncpg_pool.fetchval.return_value = 42
    repo = _make_repo()
    new_document = Data(source="example.com", content="Деканат находится в корпусе 2")

    new_id = await repo.save(new_document)

    assert new_id == 42
    args, _ = fake_asyncpg_pool.fetchval.call_args
    assert "INSERT INTO documents" in args[0]
    assert "RETURNING id" in args[0]
    assert args[1:] == (new_document.source, new_document.content, new_document.division)


async def test_delete_removes_document(fake_asyncpg_pool) -> None:
    repo = _make_repo()

    await repo.delete(1)

    args, _ = fake_asyncpg_pool.execute.call_args
    assert "DELETE FROM documents" in args[0]
    assert args[1] == 1


async def test_sources_with_prefix_maps_source_to_id(fake_asyncpg_pool) -> None:
    fake_asyncpg_pool.fetch.return_value = [{"source": "https://uust.ru/sveden/document/#abc", "id": 7}]
    repo = _make_repo()

    found = await repo.sources_with_prefix("https://uust.ru/sveden/document/")

    assert found == {"https://uust.ru/sveden/document/#abc": 7}
    sql, prefix = fake_asyncpg_pool.fetch.call_args.args
    assert "starts_with(source, $1)" in sql and prefix == "https://uust.ru/sveden/document/"


async def test_latest_with_prefix_returns_newest_records_first(fake_asyncpg_pool) -> None:
    fake_asyncpg_pool.fetch.return_value = [
        {"id": 12, "source": "https://uust.ru/news/get/x", "content": "Новость", "division": None}
    ]
    repo = _make_repo()

    found = await repo.latest_with_prefix("https://uust.ru/news/get/", 30)

    assert [item.id for item in found] == [12]
    sql, prefix, limit = fake_asyncpg_pool.fetch.call_args.args
    assert "ORDER BY id DESC" in sql and prefix == "https://uust.ru/news/get/" and limit == 30
