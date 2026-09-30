from src.domain.dialog import DialogTurn, format_history


def test_last_answer_is_kept_longer_than_older_ones() -> None:
    long_answer = "Пары: " + "x" * 1000 + " последняя до 15:25."
    turns = [
        DialogTurn(question="старый вопрос", answer=long_answer),
        DialogTurn(question="когда кончаются пары?", answer=long_answer),
    ]

    text = format_history(turns)

    # «через сколько это?» отвечается по последнему ответу - его хвост не должен обрезаться
    assert text.count("последняя до 15:25.") == 1
    assert text.endswith("последняя до 15:25.")
