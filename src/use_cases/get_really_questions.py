class GetReallyQuestions:
    """Выделяет реальные вопросы из промпта юзера - они же будут потом превращаться в embending и искаться в
    векторной базе"""

    @staticmethod
    def execute(question: str) -> list[str]:
        ...
