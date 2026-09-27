from src.use_cases.analyze_data import AnalyzeDataByLLMForUser
from src.use_cases.get_really_questions import GetReallyQuestions
from src.use_cases.search_data import SearchDataByListOfStr


class Question:
    """Входная точка, оркестратор подзадач"""

    def __init__(
        self,
        get_really_questions: GetReallyQuestions,
        search_data: SearchDataByListOfStr,
        analyze_data: AnalyzeDataByLLMForUser,
    ) -> None:
        self._get_really_questions = get_really_questions
        self._search_data = search_data
        self._analyze_data = analyze_data

    def execute(self, question: str) -> str:
        really_questions = self._get_really_questions.execute(question)
        data = self._search_data.execute(really_questions)
        return self._analyze_data.execute(question, data)
