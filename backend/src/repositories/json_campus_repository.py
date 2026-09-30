from __future__ import annotations

import json
from pathlib import Path

from src.domain.campus import Bridge, Building, Campus, Entrance, KnownRoom, Place, Stairs, Street

_CAMPUS_PATH = Path(__file__).resolve().parent / "campus.json"


def _campus_from_dict(raw: dict) -> Campus:
    return Campus(
        id=raw["id"],
        title=raw["title"],
        address=raw["address"],
        scale=raw["scale"],
        buildings=tuple(
            Building(
                id=b["id"], name=b["name"], floors=b["floors"], wings=tuple(tuple(w) for w in b["wings"]), label=b.get("label")
            )
            for b in raw["buildings"]
        ),
        bridges=tuple(
            Bridge(
                from_building=b["from"],
                to_building=b["to"],
                floors=tuple(b["floors"]),
                rect=tuple(b["rect"]),
                underground=b.get("underground", False),
            )
            for b in raw.get("bridges", [])
        ),
        stairs=tuple(Stairs(building=s["building"], at=tuple(s["at"])) for s in raw.get("stairs", [])),
        rooms=tuple(
            KnownRoom(building=r["building"], number=r["number"], floor=r["floor"], label=r["label"], at=tuple(r["at"]))
            for r in raw.get("rooms", [])
        ),
        places=tuple(
            Place(id=p["id"], kind=p["kind"], building=p["building"], floor=p["floor"], label=p["label"], at=tuple(p["at"]))
            for p in raw.get("places", [])
        ),
        entrances=tuple(Entrance(building=e["building"], at=tuple(e["at"]), dir=e["dir"]) for e in raw.get("entrances", [])),
        walkways=tuple(tuple(p) for p in raw.get("walkways", [])),
        streets=tuple(Street(name=s["name"], rect=tuple(s["rect"])) for s in raw.get("streets", [])),
    )


class JsonCampusRepository:
    """CampusRepository поверх статического campus.json (оцифровка схемы UUST MAPS)."""

    def __init__(self, path: Path = _CAMPUS_PATH) -> None:
        raw = json.loads(path.read_text(encoding="utf-8"))
        self._campuses = [_campus_from_dict(item) for item in raw["campuses"]]

    def list(self) -> list[Campus]:
        return list(self._campuses)

    def get(self, campus_id: str) -> Campus | None:
        return next((campus for campus in self._campuses if campus.id == campus_id), None)
