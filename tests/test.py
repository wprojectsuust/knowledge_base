from src.main import Question, SearchDataByListOfStr, GetReallyQuestions, AnalyzeDataByLLMForUser, NewData, Data, \
    SearchDataById, RemoveDataById, AnalyzeDataByLLMForNewData

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
    data = SearchDataById(0)
    assert isinstance(data, Data)


def test_RemoveDataById() -> None:
    assert RemoveDataById(0)
    assert not SearchDataById(0)


def test_AnalyzeDataByLLMForNewData() -> None:
    analyzed_data = AnalyzeDataByLLMForNewData.execute(test_data)
    assert isinstance(analyzed_data, list)
    assert len(analyzed_data) > 0
