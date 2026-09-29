import os
from functools import lru_cache

from src import config
from src.repositories.chroma_vector_repository import ChromaVectorRepository
from src.repositories.isu_schedule_repository import IsuScheduleRepository
from src.repositories.json_campus_repository import JsonCampusRepository
from src.repositories.postgres_data_repository import PostgresDataRepository
from src.repositories.uust_documents_repository import UustDocumentsRepository
from src.repositories.uust_news_repository import UustNewsRepository
from src.repositories.postgres_question_cache_repository import PostgresQuestionCacheRepository
from src.repositories.postgres_schedule_cache_repository import PostgresScheduleCacheRepository
from src.services.campus_service import CampusService
from src.services.data_store_service import DataStoreService
from src.services.embedding_service import EmbeddingService
from src.services.llm_service import LLMService
from src.services.news_service import NewsService
from src.services.official_documents_service import OfficialDocumentsService
from src.services.question_cache_service import QuestionCacheService
from src.services.schedule_cache_service import ScheduleCacheService
from src.services.schedule_service import ScheduleService
from src.services.vector_search_service import VectorSearchService
from src.use_cases.analyze_data import AnalyzeDataByLLMForNewData, AnalyzeDataByLLMForUser
from src.use_cases.analyze_schedule import AnalyzeScheduleForUser
from src.use_cases.build_route import BuildRoute
from src.use_cases.compose_answer import ComposeAnswer
from src.use_cases.get_schedule import GetSchedule
from src.use_cases.import_documents import ImportDocuments
from src.use_cases.import_news import ImportNews
from src.use_cases.new_data import NewData
from src.use_cases.plan_question import PlanQuestion
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


@lru_cache
def get_campus_service() -> CampusService:
    return CampusService(JsonCampusRepository())


def get_build_route_use_case() -> BuildRoute:
    return BuildRoute(get_campus_service())


def get_plan_question_use_case() -> PlanQuestion:
    return PlanQuestion(get_llm_service(), places_hint=get_campus_service().places_hint())


def get_search_data_use_case() -> SearchDataByListOfStr:
    return SearchDataByListOfStr(
        get_embedding_service(),
        get_vector_search_service(),
        get_data_store_service(),
    )


def get_search_data_by_id_use_case() -> SearchDataById:
    return SearchDataById(get_data_store_service())


def get_remove_data_use_case() -> RemoveDataById:
    return RemoveDataById(
        get_data_store_service(), get_vector_search_service(), question_cache_service=get_question_cache_service()
    )


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
        question_cache_service=get_question_cache_service(),
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
        get_plan_question_use_case(),
        get_search_data_use_case(),
        get_analyze_data_for_user_use_case(),
        get_question_cache_service(),
        get_get_schedule_use_case(),
        build_route=get_build_route_use_case(),
        compose_answer=ComposeAnswer(get_llm_service()),
    )


def get_resolve_location_use_case() -> ResolveLocation:
    return ResolveLocation()


@lru_cache
def get_news_service() -> NewsService:
    return NewsService(UustNewsRepository())


def get_import_news_use_case() -> ImportNews:
    return ImportNews(get_news_service(), get_data_store_service(), get_new_data_use_case())


def get_import_documents_use_case() -> ImportDocuments:
    return ImportDocuments(
        OfficialDocumentsService(UustDocumentsRepository()),
        get_data_store_service(),
        get_new_data_use_case(),
        get_remove_data_use_case(),
    )
