import os
from functools import lru_cache

from src import config
from src.repositories.chroma_vector_repository import ChromaVectorRepository
from src.repositories.isu_schedule_repository import IsuScheduleRepository
from src.repositories.postgres_data_repository import PostgresDataRepository
from src.repositories.postgres_question_cache_repository import PostgresQuestionCacheRepository
from src.repositories.postgres_schedule_cache_repository import PostgresScheduleCacheRepository
from src.services.data_store_service import DataStoreService
from src.services.embedding_service import EmbeddingService
from src.services.llm_service import LLMService
from src.services.question_cache_service import QuestionCacheService
from src.services.schedule_cache_service import ScheduleCacheService
from src.services.schedule_service import ScheduleService
from src.services.vector_search_service import VectorSearchService
from src.use_cases.analyze_data import AnalyzeDataByLLMForNewData, AnalyzeDataByLLMForUser
from src.use_cases.analyze_schedule import AnalyzeScheduleForUser
from src.use_cases.get_really_questions import GetReallyQuestions
from src.use_cases.get_schedule import GetSchedule
from src.use_cases.new_data import NewData
from src.use_cases.question import Question
from src.use_cases.remove_data import RemoveDataById
from src.use_cases.resolve_location import ResolveLocation
from src.use_cases.search_data import SearchDataById, SearchDataByListOfStr


@lru_cache
def get_llm_service() -> LLMService:
    return LLMService.from_env()


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService.from_env()


@lru_cache
def get_vector_search_service() -> VectorSearchService:
    repository = ChromaVectorRepository(persist_path=os.environ.get("CHROMA_PATH", "./chroma_db"))
    return VectorSearchService(repository)


def _postgres_dsn() -> str:
    user = os.environ.get("POSTGRES_USER", "uunit")
    password = os.environ.get("POSTGRES_PASSWORD", "uunit")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    database = os.environ.get("POSTGRES_DB", "uunit")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


@lru_cache
def get_data_store_service() -> DataStoreService:
    repository = PostgresDataRepository(dsn=_postgres_dsn())
    return DataStoreService(repository)


@lru_cache
def get_question_cache_service() -> QuestionCacheService:
    repository = PostgresQuestionCacheRepository(dsn=_postgres_dsn())
    return QuestionCacheService(repository)


@lru_cache
def get_schedule_service() -> ScheduleService:
    return ScheduleService(IsuScheduleRepository())


@lru_cache
def get_schedule_cache_service() -> ScheduleCacheService:
    repository = PostgresScheduleCacheRepository(dsn=_postgres_dsn(), ttl_seconds=config.SCHEDULE_CACHE_TTL_SECONDS)
    return ScheduleCacheService(repository)


def get_get_really_questions_use_case() -> GetReallyQuestions:
    return GetReallyQuestions(get_llm_service())


def get_search_data_use_case() -> SearchDataByListOfStr:
    return SearchDataByListOfStr(
        get_embedding_service(),
        get_vector_search_service(),
        get_data_store_service(),
    )


def get_search_data_by_id_use_case() -> SearchDataById:
    return SearchDataById(get_data_store_service())


def get_remove_data_use_case() -> RemoveDataById:
    return RemoveDataById(get_data_store_service(), get_vector_search_service())


def get_analyze_data_for_user_use_case() -> AnalyzeDataByLLMForUser:
    return AnalyzeDataByLLMForUser(get_llm_service())


def get_analyze_data_for_new_data_use_case() -> AnalyzeDataByLLMForNewData:
    return AnalyzeDataByLLMForNewData(get_llm_service())


def get_new_data_use_case() -> NewData:
    return NewData(
        get_analyze_data_for_new_data_use_case(),
        get_embedding_service(),
        get_vector_search_service(),
        get_data_store_service(),
    )


def get_analyze_schedule_for_user_use_case() -> AnalyzeScheduleForUser:
    return AnalyzeScheduleForUser(get_llm_service())


def get_get_schedule_use_case() -> GetSchedule:
    return GetSchedule(
        get_schedule_service(),
        get_schedule_cache_service(),
        get_embedding_service(),
        get_vector_search_service(),
        get_data_store_service(),
        get_analyze_schedule_for_user_use_case(),
    )


def get_question_use_case() -> Question:
    return Question(
        get_get_really_questions_use_case(),
        get_search_data_use_case(),
        get_analyze_data_for_user_use_case(),
        get_question_cache_service(),
        get_get_schedule_use_case(),
    )


def get_resolve_location_use_case() -> ResolveLocation:
    return ResolveLocation()
