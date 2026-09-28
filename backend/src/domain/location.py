from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class Location:
    """Место на территории УУНиТ, куда нужно попасть: корпус, и если известно - кабинет и этаж."""

    building: str
    room: str | None = None
    floor: int | None = None
