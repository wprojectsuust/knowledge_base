from dataclasses import dataclass


@dataclass(kw_only=True)
class Data:
    id: int | None = None
    source: str
    content: str
