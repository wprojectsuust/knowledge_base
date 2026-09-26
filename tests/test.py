from src.main import Question, SearchDataByText, GetReallyQuestion, AnalyzeDataByLLMForUser, NewData, Data, \
    SearchDataById, RemoveDataById, AnalyzeDataByLLMForNewData

test_data = Data(id=0, source='example.com', content="Деканат находится в корпусе 2")


def test_Question() -> None:
    answer = Question.execute(question="Мне сказали что для X нужно пойти в Y, где это?")
    assert isinstance(answer, str)
    assert len(answer) > 10


def test_GetReallyQuestion() -> None:
    task = "Мне сказали что для X нужно пойти в Y, где это?"
    really_question = GetReallyQuestion.execute(question=task)
    assert isinstance(really_question, str)
    assert 0 < len(really_question) <= len(task)


def test_SearchDataByText() -> None:
    data = SearchDataByText.execute(really_question="Где находится деканат?")
    assert isinstance(data, Data)


def test_AnalyzeDataByLLMForUser() -> None:
    prompt = "Мне сказали что для X нужно пойти в Y, где это?"
    result = AnalyzeDataByLLMForUser.execute(prompt=prompt, data=test_data)
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
