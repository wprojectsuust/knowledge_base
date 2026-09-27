from src.use_cases.analyze_data import AnalyzeDataByLLMForUser
from src.use_cases.get_really_questions import GetReallyQuestions
from src.use_cases.question import Question
from src.use_cases.search_data import SearchDataByListOfStr

test_question = "Мне сказали что для X нужно пойти в Y, где это?"


def test_question_orchestrates_full_flow(
    sample_data, make_fake_llm_service, fake_embedding_service, fake_vector_search_service, fake_data_store_service
) -> None:
    fake_vector_search_service.index(sample_data.id, [1.0])
    fake_data_store_service.store[sample_data.id] = sample_data

    get_really_questions = GetReallyQuestions(make_fake_llm_service(f'["{test_question}"]'))
    search_data = SearchDataByListOfStr(fake_embedding_service, fake_vector_search_service, fake_data_store_service)
    analyze_data = AnalyzeDataByLLMForUser(make_fake_llm_service("Деканат находится в корпусе 2, приходите пешком."))
    use_case = Question(get_really_questions, search_data, analyze_data)

    answer = use_case.execute(question=test_question)

    assert answer == "Деканат находится в корпусе 2, приходите пешком."
