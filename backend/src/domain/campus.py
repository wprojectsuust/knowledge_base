"""Кампус как граф: кабинеты, коридоры, лестницы, переходы, входы и дорожки - и поиск
маршрута по нему с шаблонным текстовым описанием.

Все координаты - пиксели схемы кампуса (см. repositories/campus.json), этаж 0 - улица.
Метры получаются умножением на Campus.scale.
"""

from __future__ import annotations

import heapq
import math
import re
from dataclasses import dataclass, field
from itertools import combinations

Rect = tuple[float, float, float, float]
Point = tuple[float, float]

_DIRECTION_VECTORS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}

ROOM_LENGTH_M = 6.0  # метров вдоль коридора на один кабинет
CORRIDOR_M = 2.4
TWO_ROWS_MIN_WIDTH_M = 10.0  # уже - кабинеты в один ряд
STAIRS_COST_M = 12.0  # «цена» одного лестничного пролёта в метрах ходьбы
OUTDOOR_PENALTY = 1.3  # по улице чуть «дороже», чем внутри, - при равенстве ведём через корпуса
OUTSIDE_OFFSET_PX = 10  # насколько точка «перед входом» отстоит от стены
WALK_SPEED_M_PER_MIN = 70


# ---------- модель ----------


@dataclass(frozen=True)
class Building:
    id: str
    name: str
    floors: int
    wings: tuple[Rect, ...]
    label: str | None = None


@dataclass(frozen=True)
class Bridge:
    from_building: str
    to_building: str
    floors: tuple[int, ...]
    rect: Rect


@dataclass(frozen=True)
class Stairs:
    building: str
    at: Point


@dataclass(frozen=True)
class KnownRoom:
    building: str
    number: str
    floor: int
    label: str
    at: Point


@dataclass(frozen=True)
class Place:
    id: str
    kind: str  # cafe | place
    building: str
    floor: int
    label: str
    at: Point


@dataclass(frozen=True)
class Entrance:
    building: str
    at: Point
    dir: str


@dataclass(frozen=True)
class Street:
    name: str
    rect: Rect


@dataclass(frozen=True)
class Campus:
    id: str
    title: str
    address: str
    scale: float
    buildings: tuple[Building, ...]
    bridges: tuple[Bridge, ...] = ()
    stairs: tuple[Stairs, ...] = ()
    rooms: tuple[KnownRoom, ...] = ()
    places: tuple[Place, ...] = ()
    entrances: tuple[Entrance, ...] = ()
    walkways: tuple[Point, ...] = ()
    streets: tuple[Street, ...] = ()

    def building(self, building_id: str) -> Building | None:
        return next((b for b in self.buildings if b.id == building_id), None)


@dataclass
class Room:
    building: str
    number: str
    floor: int
    wing: int
    rect: Rect
    label: str | None = None

    @property
    def center(self) -> Point:
        return ((self.rect[0] + self.rect[2]) / 2, (self.rect[1] + self.rect[3]) / 2)


@dataclass(frozen=True)
class RouteTarget:
    """Откуда/куда: kpp | room (7-404) | building (7) | floor (7@3) | place (place:library, place:cafe)."""

    kind: str
    building: str | None = None
    room: str | None = None
    floor: int | None = None
    place: str | None = None


@dataclass(frozen=True)
class RoutePoint:
    x: float
    y: float
    floor: int  # 0 - улица
    building: str | None = None


@dataclass
class Route:
    campus: str
    from_label: str
    to_label: str
    points: list[RoutePoint]
    steps: list[str]
    distance_m: float

    @property
    def minutes(self) -> int:
        return max(1, round(self.distance_m / WALK_SPEED_M_PER_MIN))

    def text(self) -> str:
        numbered = "\n".join(f"{i}. {step}" for i, step in enumerate(self.steps, start=1))
        return (
            f"Маршрут: {self.from_label} → {self.to_label}\n{numbered}\n"
            f"Всего около {round(self.distance_m, -1):.0f} м, примерно {self.minutes} мин. "
            "Расположение кабинетов на карте приблизительное."
        )


# ---------- разбор цели ----------

_ROOM_RE = re.compile(r"^(?P<building>[\wа-яё]+?)\s*-\s*(?P<room>\d{3}[а-яa-z]?)$", re.IGNORECASE)
_FLOOR_RE = re.compile(r"^(?P<building>[\wа-яё]+?)\s*@\s*(?P<floor>\d{1,2})$", re.IGNORECASE)


def parse_target(spec: str) -> RouteTarget | None:
    value = spec.strip()
    lowered = value.lower()
    if lowered in {"kpp", "кпп"}:
        return RouteTarget(kind="kpp")
    if lowered.startswith("place:"):
        place = lowered.removeprefix("place:").strip()
        return RouteTarget(kind="place", place=place) if place else None
    if match := _ROOM_RE.match(value):
        return RouteTarget(kind="room", building=match["building"].lower(), room=match["room"].lower())
    if match := _FLOOR_RE.match(value):
        return RouteTarget(kind="floor", building=match["building"].lower(), floor=int(match["floor"]))
    # id корпуса: "7", "ф1", "sport"; есть ли такой на карте - решает навигатор
    if re.fullmatch(r"[\wа-яё]{1,12}", lowered):
        return RouteTarget(kind="building", building=lowered)
    return None


# ---------- геометрия ----------


def _inside(point: Point, rect: Rect, shrink: float = 0.0) -> bool:
    x, y = point
    return rect[0] + shrink < x < rect[2] - shrink and rect[1] + shrink < y < rect[3] - shrink


def _spine(rect: Rect) -> tuple[bool, float, float, float]:
    """Ось коридора крыла: (вдоль x?, координата оси поперёк, начало, конец вдоль)."""
    x1, y1, x2, y2 = rect
    along_x = (x2 - x1) >= (y2 - y1)
    if along_x:
        inset = min((y2 - y1) / 2, 4)
        return True, (y1 + y2) / 2, x1 + inset, x2 - inset
    inset = min((x2 - x1) / 2, 4)
    return False, (x1 + x2) / 2, y1 + inset, y2 - inset


def _project(rect: Rect, point: Point) -> tuple[float, Point]:
    along_x, across, start, end = _spine(rect)
    t = min(max(point[0] if along_x else point[1], start), end)
    return t, ((t, across) if along_x else (across, t))


def _distance_to_rect(rect: Rect, point: Point) -> float:
    dx = max(rect[0] - point[0], 0, point[0] - rect[2])
    dy = max(rect[1] - point[1], 0, point[1] - rect[3])
    return math.hypot(dx, dy)


def _rects_touch(a: Rect, b: Rect, tolerance: float = 3) -> Rect | None:
    x1, y1 = max(a[0], b[0]) - tolerance, max(a[1], b[1]) - tolerance
    x2, y2 = min(a[2], b[2]) + tolerance, min(a[3], b[3]) + tolerance
    return (x1, y1, x2, y2) if x1 <= x2 and y1 <= y2 else None


# ---------- кабинеты ----------


def generate_rooms(campus: Campus, building: Building) -> list[Room]:
    """Раскладка кабинетов: коридор по длинной оси крыла, кабинеты по обе стороны, нумерация
    «этаж + порядковый номер» как в ИСУ. Приблизительная - реальных планов этажей нет;
    известные кабинеты (campus.rooms) ставятся точно на своё место."""
    rooms: list[Room] = []
    px = 1 / campus.scale
    for floor in range(1, building.floors + 1):
        counter = 1
        for wing_index, (x1, y1, x2, y2) in enumerate(building.wings):
            along_x = (x2 - x1) >= (y2 - y1)
            long = (x2 - x1) if along_x else (y2 - y1)
            short = (y2 - y1) if along_x else (x2 - x1)
            count = max(1, int(long // (ROOM_LENGTH_M * px)))
            length = long / count
            rows = 2 if short >= TWO_ROWS_MIN_WIDTH_M * px else 1
            corridor = CORRIDOR_M * px if rows == 2 else 0
            depth = (short - corridor) / rows
            for row in range(rows):
                across_start = (y1 if along_x else x1) + row * (depth + corridor)
                for i in range(count):
                    along_start = (x1 if along_x else y1) + i * length
                    rect = (
                        (along_start, across_start, along_start + length, across_start + depth)
                        if along_x
                        else (across_start, along_start, across_start + depth, along_start + length)
                    )
                    rooms.append(Room(building.id, f"{floor}{counter:02d}", floor, wing_index, rect))
                    counter += 1

    for known in (r for r in campus.rooms if r.building == building.id):
        on_floor = [room for room in rooms if room.floor == known.floor]
        if not on_floor:
            continue
        cell = next((room for room in on_floor if _inside(known.at, room.rect)), None) or min(
            on_floor, key=lambda room: math.dist(room.center, known.at)
        )
        clash = next((room for room in on_floor if room is not cell and room.number == known.number), None)
        if clash:
            clash.number = cell.number
        cell.number = known.number
        cell.label = known.label
    return rooms


# ---------- граф и маршрут ----------


@dataclass
class _Node:
    id: str
    point: Point
    floor: int
    building: str | None
    kind: str  # corridor | room | stairs | bridge | door | outside | place
    label: str | None = None


@dataclass
class _Graph:
    nodes: dict[str, _Node] = field(default_factory=dict)
    edges: dict[str, list[tuple[str, float]]] = field(default_factory=dict)

    def add(self, node: _Node) -> str:
        self.nodes.setdefault(node.id, node)
        self.edges.setdefault(node.id, [])
        return node.id

    def link(self, a: str, b: str, cost: float) -> None:
        if a == b:
            return
        self.edges[a].append((b, cost))
        self.edges[b].append((a, cost))


class CampusNavigator:
    """Строит граф кампуса один раз и отвечает на запросы маршрутов."""

    def __init__(self, campus: Campus) -> None:
        self.campus = campus
        self._rooms = {b.id: generate_rooms(campus, b) for b in campus.buildings}
        self._graph = _Graph()
        # точки, «пристёгнутые» к оси коридора крыла: (корпус, этаж, крыло) -> [(t, node_id)]
        self._spines: dict[tuple[str, int, int], list[tuple[float, str]]] = {}
        self._build()

    # --- публичное ---

    def rooms(self, building_id: str) -> list[Room]:
        return self._rooms.get(building_id, [])

    def segment_is_clear(self, a: Point, b: Point) -> bool:
        """Отрезок по улице не проходит сквозь корпуса и наземные переходы."""
        obstacles = [wing for building in self.campus.buildings for wing in building.wings]
        obstacles += [bridge.rect for bridge in self.campus.bridges if 1 in bridge.floors]
        steps = max(2, int(math.dist(a, b) // 2))
        for i in range(1, steps):
            t = i / steps
            p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            if any(_inside(p, rect, shrink=2) for rect in obstacles):
                return False
        return True

    def route(self, source: RouteTarget | None, target: RouteTarget | None) -> Route | None:
        if source is None or target is None:
            return None
        starts = self._resolve(source)
        ends = self._resolve(target)
        if not starts or not ends:
            return None
        path = self._dijkstra(starts, ends)
        if path is None:
            return None

        nodes = [self._graph.nodes[node_id] for node_id in path]
        points = [RoutePoint(n.point[0], n.point[1], n.floor, n.building) for n in nodes]
        distance = sum(
            self._edge_meters(a, b) for a, b in zip(nodes, nodes[1:])
        )
        return Route(
            campus=self.campus.id,
            from_label=self._label(source, nodes[0]),
            to_label=self._label(target, nodes[-1]),
            points=points,
            steps=self._describe(nodes, self._label(source, nodes[0]), self._label(target, nodes[-1])),
            distance_m=distance,
        )

    # --- построение графа ---

    def _attach(self, building: Building, floor: int, point: Point, node: _Node, wing: int | None = None) -> None:
        """Добавляет узел и соединяет его с ближайшей точкой оси коридора на этом этаже."""
        g = self._graph
        g.add(node)
        if wing is None:
            wing = min(range(len(building.wings)), key=lambda i: _distance_to_rect(building.wings[i], point))
        t, projected = _project(building.wings[wing], point)
        corridor_id = f"c:{building.id}:{floor}:{wing}:{t:.1f}"
        g.add(_Node(corridor_id, projected, floor, building.id, "corridor"))
        self._spines.setdefault((building.id, floor, wing), []).append((t, corridor_id))
        g.link(node.id, corridor_id, math.dist(point, projected) * self.campus.scale)

    def _build(self) -> None:
        campus, g = self.campus, self._graph

        for building in campus.buildings:
            for floor in range(1, building.floors + 1):
                # концы коридоров и стыки крыльев
                for wing_index, wing in enumerate(building.wings):
                    along_x, across, start, end = _spine(wing)
                    for t in (start, end):
                        point = (t, across) if along_x else (across, t)
                        node = _Node(f"end:{building.id}:{floor}:{wing_index}:{t:.1f}", point, floor, building.id, "corridor")
                        self._attach(building, floor, point, node, wing_index)
                for (i, a), (j, b) in combinations(enumerate(building.wings), 2):
                    contact = _rects_touch(a, b)
                    if contact is None:
                        continue
                    point = ((contact[0] + contact[2]) / 2, (contact[1] + contact[3]) / 2)
                    node = _Node(f"joint:{building.id}:{floor}:{i}:{j}", point, floor, building.id, "corridor")
                    self._attach(building, floor, point, node, i)
                    self._attach(building, floor, point, node, j)

            for room in self._rooms[building.id]:
                node = _Node(f"r:{building.id}:{room.number}", room.center, room.floor, building.id, "room")
                self._attach(building, room.floor, room.center, node, room.wing)

        for index, stairs in enumerate(campus.stairs):
            building = campus.building(stairs.building)
            if building is None:
                continue
            previous = None
            for floor in range(1, building.floors + 1):
                node_id = f"s:{building.id}:{index}:{floor}"
                self._attach(building, floor, stairs.at, _Node(node_id, stairs.at, floor, building.id, "stairs"))
                if previous:
                    g.link(previous, node_id, STAIRS_COST_M)
                previous = node_id

        for index, bridge in enumerate(campus.bridges):
            center = ((bridge.rect[0] + bridge.rect[2]) / 2, (bridge.rect[1] + bridge.rect[3]) / 2)
            for floor in bridge.floors:
                ends = []
                for building_id in (bridge.from_building, bridge.to_building):
                    building = campus.building(building_id)
                    if building is None or floor > building.floors:
                        break
                    node_id = f"b:{index}:{floor}:{building_id}"
                    self._attach(building, floor, center, _Node(node_id, center, floor, building_id, "bridge"))
                    ends.append(node_id)
                if len(ends) == 2:
                    g.link(ends[0], ends[1], max(bridge.rect[2] - bridge.rect[0], bridge.rect[3] - bridge.rect[1]) * campus.scale)

        for place in campus.places:
            building = campus.building(place.building)
            if building is not None and place.floor <= building.floors:
                node = _Node(f"p:{place.id}", place.at, place.floor, building.id, "place", place.label)
                self._attach(building, place.floor, place.at, node)

        outdoor: list[str] = []
        for index, entrance in enumerate(campus.entrances):
            building = campus.building(entrance.building)
            if building is None:
                continue
            dx, dy = _DIRECTION_VECTORS[entrance.dir]
            outside = (entrance.at[0] - dx * OUTSIDE_OFFSET_PX, entrance.at[1] - dy * OUTSIDE_OFFSET_PX)
            door_id = f"d:{building.id}:{index}"
            self._attach(building, 1, entrance.at, _Node(door_id, entrance.at, 1, building.id, "door"))
            outside_id = g.add(_Node(f"o:{index}", outside, 0, None, "outside", building.id))
            g.link(door_id, outside_id, OUTSIDE_OFFSET_PX * campus.scale)
            outdoor.append(outside_id)
        for index, point in enumerate(campus.walkways):
            outdoor.append(g.add(_Node(f"w:{index}", point, 0, None, "outside")))
        for a, b in combinations(outdoor, 2):
            pa, pb = g.nodes[a].point, g.nodes[b].point
            if self.segment_is_clear(pa, pb):
                g.link(a, b, math.dist(pa, pb) * campus.scale * OUTDOOR_PENALTY)

        # соединяем соседние точки вдоль каждой оси коридора
        for attachments in self._spines.values():
            ordered = sorted(set(attachments))
            for (t1, a), (t2, b) in zip(ordered, ordered[1:]):
                g.link(a, b, abs(t2 - t1) * campus.scale)

    # --- поиск ---

    def _resolve(self, target: RouteTarget) -> set[str]:
        nodes = self._graph.nodes.values()
        if target.kind == "kpp":
            return {n.id for n in nodes if n.kind == "outside" and n.label == "kpp"}
        if target.kind == "place":
            return {
                n.id
                for n in nodes
                if n.kind == "place" and (n.id == f"p:{target.place}" or n.id.startswith(f"p:{target.place}-"))
            }
        if target.building is None or self.campus.building(target.building) is None:
            return set()
        if target.kind == "room":
            room = self._find_room(target.building, target.room or "")
            if room is not None:
                return {f"r:{room.building}:{room.number}"}
            # такого номера нет в раскладке - ведём хотя бы на нужный этаж
            floor = int((target.room or "0")[0])
            return self._resolve(RouteTarget(kind="floor", building=target.building, floor=floor))
        if target.kind == "floor":
            return {
                n.id
                for n in nodes
                if n.building == target.building and n.floor == target.floor and n.kind in {"stairs", "bridge"}
            }
        if target.kind == "building":
            return {n.id for n in nodes if n.kind == "door" and n.building == target.building}
        return set()

    def _find_room(self, building_id: str, number: str) -> Room | None:
        rooms = self._rooms.get(building_id, [])
        digits = re.sub(r"\D+$", "", number)
        return next((r for r in rooms if r.number == number), None) or next(
            (r for r in rooms if r.number == digits), None
        )

    def _dijkstra(self, starts: set[str], ends: set[str]) -> list[str] | None:
        distances = {node: 0.0 for node in starts}
        previous: dict[str, str] = {}
        queue = [(0.0, node) for node in starts]
        heapq.heapify(queue)
        while queue:
            cost, node = heapq.heappop(queue)
            if cost > distances.get(node, math.inf):
                continue
            if node in ends:
                path = [node]
                while path[-1] in previous:
                    path.append(previous[path[-1]])
                return path[::-1]
            for neighbour, weight in self._graph.edges[node]:
                new_cost = cost + weight
                if new_cost < distances.get(neighbour, math.inf):
                    distances[neighbour] = new_cost
                    previous[neighbour] = node
                    heapq.heappush(queue, (new_cost, neighbour))
        return None

    def _edge_meters(self, a: _Node, b: _Node) -> float:
        if a.kind == "stairs" and b.kind == "stairs" and a.floor != b.floor:
            return 8.0  # реальная длина пролёта, без «штрафа» за подъём
        return math.dist(a.point, b.point) * self.campus.scale

    # --- текст ---

    def _building_name(self, building_id: str | None) -> str:
        building = self.campus.building(building_id or "")
        if building is None:
            return ""
        if building.id == "kpp":
            return "КПП"
        if building.id.isdigit():
            return f"корпус {building.id}"
        # "Спортзал" -> "спортзал": имя идёт внутри фразы ("Войдите в спортзал")
        name = building.label or building.name
        return name[0].lower() + name[1:]

    def _label(self, target: RouteTarget, node: _Node) -> str:
        if target.kind == "kpp":
            return "КПП"
        if target.kind == "room":
            room = self._find_room(target.building or "", target.room or "")
            name = f"кабинет {target.building}-{room.number if room else target.room}"
            return f"{name} ({room.label})" if room and room.label else name
        if target.kind == "floor":
            return f"{self._building_name(target.building)}, {target.floor} этаж"
        if target.kind == "building":
            return self._building_name(target.building)
        if target.kind == "place":
            building = self._building_name(node.building)
            return f"{node.label} ({building}, {node.floor} этаж)"
        return "?"

    def _describe(self, nodes: list[_Node], from_label: str, to_label: str) -> list[str]:
        steps = [f"Старт: {from_label}."]
        walked = 0.0  # метров пройдено с последней озвученной точки

        def meters() -> str:
            return f" (~{max(5, round(walked, -1)):.0f} м)" if walked >= 5 else ""

        i = 0
        while i < len(nodes) - 1:
            a, b = nodes[i], nodes[i + 1]
            walked += self._edge_meters(a, b)

            if a.kind == "stairs" and b.kind == "stairs" and a.floor != b.floor:
                # схлопываем все пролёты подряд в одну фразу
                j = i + 1
                while j + 1 < len(nodes) and nodes[j + 1].kind == "stairs" and nodes[j + 1].building == a.building:
                    j += 1
                target_floor = nodes[j].floor
                verb = "Поднимитесь" if target_floor > a.floor else "Спуститесь"
                steps.append(f"{verb} по лестнице на {target_floor} этаж.")
                walked = 0.0
                i = j
                continue
            if a.kind == "bridge" and b.kind == "bridge" and a.building != b.building:
                steps.append(f"Пройдите по переходу на {a.floor} этаже в {self._building_name(b.building)}{meters()}.")
                walked = 0.0
            elif a.kind == "outside" and b.kind == "door":
                if b.building == "kpp":
                    steps.append(f"Пройдите через КПП{meters()}.")
                else:
                    steps.append(f"Войдите в {self._building_name(b.building)}{meters()}.")
                walked = 0.0
            elif a.kind == "door" and b.kind == "outside" and a.building != "kpp":
                steps.append(f"Выйдите из {self._building_name(a.building).replace('корпус', 'корпуса')} на улицу.")
                walked = 0.0
            i += 1

        steps.append(f"Вы на месте: {to_label}{meters()}.")
        return steps
