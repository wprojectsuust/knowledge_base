import pytest

from src.domain.location import Location
from src.use_cases.resolve_location import ResolveLocation


@pytest.fixture
def use_case() -> ResolveLocation:
    return ResolveLocation()


@pytest.mark.parametrize(
    ("question", "answer", "expected"),
    [
        ("как дойти до 7-404?", "", Location(building="7", room="404", floor=4)),
        ("где кабинет 3-106б", "", Location(building="3", room="106б", floor=1)),
        ("где у меня пара?", "Матанализ в 09:00, кабинет 7-404.", Location(building="7", room="404", floor=4)),
        ("как добраться до 5 корпуса", "", Location(building="5")),
        ("где находится деканат?", "Деканат находится в корпусе 2, кабинет 214.", Location(building="2")),
        ("где находится деканат?", "Деканат находится в 3-м корпусе.", Location(building="3")),
    ],
)
async def test_resolves_location_from_question_or_answer(use_case, question, answer, expected) -> None:
    assert await use_case.execute(question, answer) == expected


async def test_question_location_wins_over_answer_location(use_case) -> None:
    location = await use_case.execute("как дойти до 7-404?", "Пройдите через корпус 1.")

    assert location == Location(building="7", room="404", floor=4)


@pytest.mark.parametrize(
    ("question", "answer"),
    [
        # не навигационный вопрос - даже если в ответе упомянут корпус, карта не нужна
        ("какие есть стипендии?", "Документы сдаются в корпусе 2."),
        # навигационный вопрос, но места в тексте нет
        ("где найти методички?", "Методички есть в электронной библиотеке."),
        # даты, время и код группы не должны приниматься за кабинет
        ("где у меня пара 30-09-2026?", "Группа 1-1.1.1.-26А: 09:00-10:30 Матанализ."),
    ],
)
async def test_returns_none_when_no_place(use_case, question, answer) -> None:
    assert await use_case.execute(question, answer) is None
