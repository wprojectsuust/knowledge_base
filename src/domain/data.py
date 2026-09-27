from dataclasses import dataclass


@dataclass
class Data:
    id: int
    source: str
    content: str
