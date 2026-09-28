from dataclasses import dataclass

from src.domain.campus import Route


@dataclass(kw_only=True)
class Answer:
    """Итоговый ответ на сообщение: текст (возможно, склеенный из нескольких частей) и маршрут,
    если студент спрашивал, как пройти."""

    text: str
    route: Route | None = None
