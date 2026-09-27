from src.domain.data import Data
from src.use_cases.question import Question
from src.use_cases.get_really_questions import GetReallyQuestions
from src.use_cases.search_data import SearchDataByListOfStr, SearchDataById
from src.use_cases.remove_data import RemoveDataById
from src.use_cases.new_data import NewData
from src.use_cases.analyze_data import AnalyzeDataByLLMForUser, AnalyzeDataByLLMForNewData

test_data = Data(id=0, source='example.com', content="Деканат находится в корпусе 2")
test_task = "Мне сказали что для X нужно пойти в Y, где это?"


def test_Question() -> None:
    answer = Question.execute(question="Мне сказали что для X нужно пойти в Y, где это?")
    assert isinstance(answer, str)
    assert len(answer) > 10


def test_GetReallyQuestions() -> None:
    really_questions = GetReallyQuestions.execute(question=test_task)
    assert isinstance(really_questions, list)
    assert 0 < len(really_questions)


def test_SearchDataByText() -> None:
    data = SearchDataByListOfStr.execute(really_question=["Где находится деканат?"])
    assert isinstance(data, list)
    assert isinstance(data[0], Data)


def test_AnalyzeDataByLLMForUser() -> None:
    result = AnalyzeDataByLLMForUser.execute(prompt=test_task, data=[test_data])
    assert isinstance(result, str)
    assert len(result) > 5


def test_NewData() -> None:
    assert NewData.execute(test_data)


def test_SearchDataById() -> None:
    data = SearchDataById.execute(0)
    assert isinstance(data, Data)


def test_RemoveDataById() -> None:
    assert RemoveDataById.execute(0)
    assert not SearchDataById.execute(0)


def test_AnalyzeDataByLLMForNewData() -> None:
    analyzed_data = AnalyzeDataByLLMForNewData.execute(test_data)
    assert isinstance(analyzed_data, list)
    assert len(analyzed_data) > 0
