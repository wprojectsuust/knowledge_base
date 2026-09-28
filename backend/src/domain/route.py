from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class RouteRequest:
    """Пользователь спросил, как пройти: откуда (None - от КПП) и куда, в нотации навигатора
    (kpp, 7-404, 7, 7@3, place:library, place:cafe - см. domain.campus.parse_target)."""

    source: str | None
    target: str
