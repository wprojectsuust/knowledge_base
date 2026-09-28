from src.domain.clarification import KnownFact, compose_question


def test_compose_question_without_facts_returns_question_as_is() -> None:
    assert compose_question("какое у меня завтра расписание", []) == "какое у меня завтра расписание"


def test_compose_question_appends_known_facts() -> None:
    composed = compose_question("какое у меня завтра расписание", [KnownFact(field="group", value="ПРО-101")])

    assert composed.startswith("какое у меня завтра расписание")
    assert "group: ПРО-101" in composed
