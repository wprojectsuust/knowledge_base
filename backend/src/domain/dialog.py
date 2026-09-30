from dataclasses import dataclass

# сколько последних реплик чата учитывать и сколько символов ответа из каждой брать -
# для понимания «а туда как пройти?» этого хватает, а токены не раздуваются
MAX_TURNS = 6
MAX_ANSWER_CHARS = 600
# последний ответ - почти целиком: на него чаще всего ссылаются («через сколько это?»)
MAX_LAST_ANSWER_CHARS = 2000


@dataclass(frozen=True, kw_only=True)
class DialogTurn:
    """Одна реплика чата: вопрос студента и ответ консультанта. Чат хранится только в браузере,
    сервер получает последние реплики с каждым вопросом и нигде их не сохраняет."""

    question: str
    answer: str


def format_history(turns: list[DialogTurn]) -> str:
    lines = []
    recent = turns[-MAX_TURNS:]
    for index, turn in enumerate(recent):
        limit = MAX_LAST_ANSWER_CHARS if index == len(recent) - 1 else MAX_ANSWER_CHARS
        answer = turn.answer if len(turn.answer) <= limit else turn.answer[:limit] + "…"
        lines.append(f"Студент: {turn.question}\nКонсультант: {answer}")
    return "\n\n".join(lines)
