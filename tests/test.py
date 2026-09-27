from src.domain.data import Data
from src.use_cases.analyze_data import AnalyzeDataByLLMForNewData, AnalyzeDataByLLMForUser
from src.use_cases.get_really_questions import GetReallyQuestions
from src.use_cases.new_data import NewData
from src.use_cases.question import Question
from src.use_cases.remove_data import RemoveDataById
from src.use_cases.search_data import SearchDataById, SearchDataByListOfStr

test_data = Data(id=0, source='example.com', content="Деканат находится в корпусе 2")
test_task = "Мне сказали что для X нужно пойти в Y, где это?"


class FakeLLMService:
    def __init__(self, response: str) -> None:
        self._response = response

    def generate(self, prompt: str) -> str:
        return self._response


class FakeEmbeddingService:
    def encode(self, text: str) -> list[float]:
        return [float(len(text))]


class FakeVectorSearchService:
    def __init__(self) -> None:
        self._index: dict[int, list[float]] = {}

    def search(self, embedding: list[float], n_results: int = 6) -> list[int]:
        return list(self._index.keys())[:n_results]

    def index(self, id_: int, embedding: list[float]) -> None:
        self._index[id_] = embedding

    def remove(self, id_: int) -> None:
        self._index.pop(id_, None)


class FakeDataStoreService:
    def __init__(self, seed: dict[int, Data] | None = None) -> None:
        self._store: dict[int, Data] = dict(seed or {})

    def get(self, id_: int) -> Data | None:
        return self._store.get(id_)

    def get_many(self, ids: list[int]) -> list[Data]:
        return [self._store[id_] for id_ in ids if id_ in self._store]

    def save(self, data: Data) -> None:
        self._store[data.id] = data

    def remove(self, id_: int) -> None:
        self._store.pop(id_, None)


def test_GetReallyQuestions() -> None:
    use_case = GetReallyQuestions(FakeLLMService('["Где находится деканат?"]'))

    really_questions = use_case.execute(question=test_task)

    assert isinstance(really_questions, list)
    assert really_questions == ["Где находится деканат?"]


def test_SearchDataByListOfStr() -> None:
    vector_search = FakeVectorSearchService()
    vector_search.index(test_data.id, [1.0])
    store = FakeDataStoreService(seed={test_data.id: test_data})
    use_case = SearchDataByListOfStr(FakeEmbeddingService(), vector_search, store)

    data = use_case.execute(really_question=["Где находится деканат?"])

    assert data == [test_data]


def test_AnalyzeDataByLLMForUser() -> None:
    use_case = AnalyzeDataByLLMForUser(FakeLLMService("В корпусе 2, деканат."))

    result = use_case.execute(prompt=test_task, data=[test_data])

    assert isinstance(result, str)
    assert len(result) > 5


def test_AnalyzeDataByLLMForNewData() -> None:
    use_case = AnalyzeDataByLLMForNewData(FakeLLMService('["где деканат", "как найти деканат"]'))

    questions = use_case.execute(test_data)

    assert isinstance(questions, list)
    assert questions == ["где деканат", "как найти деканат"]


def test_NewData() -> None:
    store = FakeDataStoreService()
    vector_search = FakeVectorSearchService()
    analyze_data = AnalyzeDataByLLMForNewData(FakeLLMService('["где деканат"]'))
    use_case = NewData(analyze_data, FakeEmbeddingService(), vector_search, store)

    assert use_case.execute(test_data)
    assert store.get(test_data.id) == test_data


def test_SearchDataById() -> None:
    store = FakeDataStoreService(seed={test_data.id: test_data})
    use_case = SearchDataById(store)

    data = use_case.execute(test_data.id)

    assert isinstance(data, Data)


def test_RemoveDataById() -> None:
    store = FakeDataStoreService(seed={test_data.id: test_data})
    vector_search = FakeVectorSearchService()
    vector_search.index(test_data.id, [1.0])
    remove_use_case = RemoveDataById(store, vector_search)
    search_use_case = SearchDataById(store)

    assert remove_use_case.execute(test_data.id)
    assert not search_use_case.execute(test_data.id)


def test_Question() -> None:
    vector_search = FakeVectorSearchService()
    vector_search.index(test_data.id, [1.0])
    store = FakeDataStoreService(seed={test_data.id: test_data})

    get_really_questions = GetReallyQuestions(FakeLLMService(f'["{test_task}"]'))
    search_data = SearchDataByListOfStr(FakeEmbeddingService(), vector_search, store)
    analyze_data = AnalyzeDataByLLMForUser(FakeLLMService("Деканат находится в корпусе 2, приходите пешком."))
    use_case = Question(get_really_questions, search_data, analyze_data)

    answer = use_case.execute(question=test_task)

    assert isinstance(answer, str)
    assert len(answer) > 10
