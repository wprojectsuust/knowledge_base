from src.domain.event import FORMATS, TOPICS, normalize_format, normalize_topic


def test_topic_and_format_from_llm_are_mapped_to_catalog_values() -> None:
    assert normalize_topic("карьера и бизнес") == "Карьера и бизнес"
    assert normalize_format(" Мастер-класс ") == "Мастер-класс"


def test_unknown_values_fall_back_to_other_so_filters_stay_consistent() -> None:
    assert normalize_topic("кулинария") == "Другое"
    assert normalize_format(None) == "Другое"
    assert TOPICS[-1] == "Другое" and FORMATS[-1] == "Другое"


import pytest

from src.domain.event import guess_labels


@pytest.mark.parametrize(
    ("title", "topic", "fmt", "online"),
    [
        ("Сбор сведений для участия в конкурсе на назначение стипендии Президента РФ", "Стипендии и гранты", "Конкурс", False),
        ("Карьерные консультации", "Карьера и бизнес", "Консультация", False),
        ("Пробный ЕГЭ по обществознанию: разберем самые сложные задания", "Учёба и поступление", "Мастер-класс", False),
        ("Международная конференция «Физика и технология перспективных материалов»", "Наука и технологии", "Конференция и форум", False),
        ("Онлайн-турнир по шахматам среди студентов", "Спорт и здоровье", "Соревнование и игра", True),
        ("Праздничный концерт ко Дню учителя", "Творчество и культура", "Фестиваль и праздник", False),
        ("Что-то непонятное", "Другое", "Другое", False),
    ],
)
def test_keyword_labels_are_a_sane_fallback_when_llm_is_down(title, topic, fmt, online) -> None:
    assert guess_labels(title) == (topic, fmt, online)
