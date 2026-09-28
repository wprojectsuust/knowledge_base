from src.repositories.postgres_question_cache_repository import PostgresQuestionCacheRepository


def _make_repo() -> PostgresQuestionCacheRepository:
    return PostgresQuestionCacheRepository(dsn="postgresql://uunit:uunit@localhost:5432/uunit")


async def test_creates_question_cache_table_on_first_use(fake_asyncpg_pool) -> None:
    repo = _make_repo()

    await repo.get("где деканат")

    create_table_call = fake_asyncpg_pool.execute.call_args_list[0]
    assert "CREATE TABLE IF NOT EXISTS question_cache" in create_table_call.args[0]


async def test_get_returns_cached_answer_when_present(fake_asyncpg_pool) -> None:
    fake_asyncpg_pool.fetchval.return_value = "Деканат в корпусе 2."
    repo = _make_repo()

    result = await repo.get("где деканат")

    assert result == "Деканат в корпусе 2."
    args, _ = fake_asyncpg_pool.fetchval.call_args
    assert "SELECT answer FROM question_cache" in args[0]
    assert args[1] == "где деканат"


async def test_get_returns_none_on_cache_miss(fake_asyncpg_pool) -> None:
    fake_asyncpg_pool.fetchval.return_value = None
    repo = _make_repo()

    assert await repo.get("неизвестный вопрос") is None


async def test_save_upserts_question_answer_pair(fake_asyncpg_pool) -> None:
    repo = _make_repo()

    await repo.save("где деканат", "Деканат в корпусе 2.")

    args, _ = fake_asyncpg_pool.execute.call_args_list[-1]
    assert "INSERT INTO question_cache" in args[0]
    assert "ON CONFLICT (question) DO UPDATE" in args[0]
    assert args[1:] == ("где деканат", "Деканат в корпусе 2.")
