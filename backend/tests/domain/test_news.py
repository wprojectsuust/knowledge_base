import pytest

from src.domain.data import Data
from src.domain.news import is_news_question, newest_first


@pytest.mark.parametrize(
    "question",
    [
        "Какие есть мероприятия?",
        "что нового в универе",
        "Какие события на этой неделе?",
        "последние новости УУНиТ",
        "будет ли какой-нибудь концерт или фестиваль?",
    ],
)
def test_detects_questions_about_events_and_news(question) -> None:
    assert is_news_question(question)


@pytest.mark.parametrize(
    "question", ["Где находится деканат?", "Как получить справку об обучении?", "Кто мой тьютор?"]
)
def test_ordinary_questions_are_not_about_news(question) -> None:
    assert not is_news_question(question)


def test_newest_first_orders_by_publication_date_in_text() -> None:
    old = Data(id=5, source="https://uust.ru/news/get/a", content="Новость УУНиТ от 20.09.2026: Старое")
    fresh = Data(id=3, source="https://uust.ru/news/get/b", content="Новость УУНиТ от 28.09.2026: Свежее")
    undated = Data(id=9, source="https://uust.ru/news/get/c", content="Без даты")

    # id не равен порядку публикации: импорт идёт от новых к старым
    assert newest_first([old, undated, fresh], limit=2) == [fresh, old]
