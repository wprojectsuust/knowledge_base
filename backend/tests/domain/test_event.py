from src.domain.event import FORMATS, TOPICS, normalize_format, normalize_topic


def test_topic_and_format_from_llm_are_mapped_to_catalog_values() -> None:
    assert normalize_topic("карьера и бизнес") == "Карьера и бизнес"
    assert normalize_format(" Мастер-класс ") == "Мастер-класс"


def test_unknown_values_fall_back_to_other_so_filters_stay_consistent() -> None:
    assert normalize_topic("кулинария") == "Другое"
    assert normalize_format(None) == "Другое"
    assert TOPICS[-1] == "Другое" and FORMATS[-1] == "Другое"
