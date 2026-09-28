from pathlib import Path

from src.domain.news import NewsHeadline
from src.repositories.uust_news_repository import parse_article_text, parse_news_list

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_parse_news_list_extracts_cards_with_absolute_urls_and_dates() -> None:
    headlines = parse_news_list((FIXTURES / "uust_news_list.html").read_text(encoding="utf-8"))

    assert headlines == [
        NewsHeadline(
            url="https://uust.ru/news/get/konferenciya-po-bioraznoobraziyu",
            title="Память, наука, практика – V Международная конференция по биоразнообразию",
            published_at="2026-09-28T15:00:57+05:00",
        ),
        NewsHeadline(
            url="https://uust.ru/news/get/osennij-subbotnik",
            title="Осенний субботник в УУНиТ",
            published_at="2026-09-27T10:31:23+05:00",
        ),
    ]


def test_parse_article_text_takes_only_the_news_body() -> None:
    text = parse_article_text((FIXTURES / "uust_news_item.html").read_text(encoding="utf-8"))

    assert text == (
        "Золотая осень — это не просто время года для студентов.\n"
        "Субботник прошёл во всех корпусах, собрали сотни мешков мусора."
    )


def test_parse_article_text_returns_none_when_no_body() -> None:
    assert parse_article_text("<html><body><p>Страница не найдена</p></body></html>") is None
