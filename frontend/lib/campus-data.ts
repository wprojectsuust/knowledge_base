/**
 * Данные для 3D-карты кампусов. Сцена целиком строится из этого файла - после обхода
 * достаточно поправить цифры здесь, код трогать не нужно.
 *
 * Кампус УГАТУ оцифрован со схемы UUST MAPS (example/karla.jpg, 1280×811): ВСЕ координаты -
 * пиксели этой картинки. Прямоугольник [x1, y1, x2, y2] - левый верхний и правый нижний угол.
 * Масштаб scale переводит пиксели в метры (0.4 м/px -> корпус 1 примерно 130 м в длину).
 *
 * Корпус = несколько прямоугольных «крыльев» (Г- и П-образные корпуса), вытянутых на floors
 * этажей. Этажность, кроме корпусов 7 и 9, пока ПРИМЕРНАЯ.
 */

export type Rect = [number, number, number, number];
export type Point = [number, number];
/** куда смотрит стрелка входа на схеме: down - вниз по картинке и т.д. */
export type Direction = "up" | "down" | "left" | "right";

export type Building = {
  /** как в ИСУ/расписании: "Корпус 7" -> id "7" */
  id: string;
  name: string;
  wings: Rect[];
  floors: number;
  /** подпись над корпусом на карте; по умолчанию id */
  label?: string;
};

export type Bridge = {
  from: string;
  to: string;
  /** на каких этажах есть переход */
  floors: number[];
  rect: Rect;
};

/** Кабинет, чьё место известно точно (со схемы или с обхода). Остальные раскладываются автоматически. */
export type KnownRoom = {
  building: string;
  number: string;
  floor: number;
  label: string;
  at: Point;
};

export type Place = {
  kind: "cafe" | "place";
  building: string;
  floor: number;
  label: string;
  at: Point;
};

export type Entrance = {
  building: string;
  at: Point;
  dir: Direction;
  main?: boolean;
};

export type Street = {
  name: string;
  rect: Rect;
};

export type Campus = {
  id: string;
  title: string;
  address: string;
  /** метров в одном пикселе схемы */
  scale: number;
  buildings: Building[];
  bridges: Bridge[];
  rooms: KnownRoom[];
  places: Place[];
  entrances: Entrance[];
  streets: Street[];
};

export const FLOOR_HEIGHT = 4;

export const CAMPUSES: Campus[] = [
  {
    id: "ugatu",
    title: "Кампус УГАТУ",
    address: "ул. Карла Маркса, 12",
    scale: 0.4,
    buildings: [
      {
        id: "1",
        name: "Корпус 1",
        floors: 5,
        wings: [
          [562, 405, 895, 470],
          [565, 470, 607, 560],
          [895, 405, 935, 530],
        ],
      },
      { id: "2", name: "Корпус 2", floors: 5, wings: [[365, 285, 525, 330], [440, 330, 520, 530]] },
      {
        id: "3",
        name: "Корпус 3",
        floors: 4,
        wings: [
          [120, 385, 165, 530],
          [165, 475, 280, 530],
          [165, 330, 290, 385],
        ],
      },
      {
        id: "4",
        name: "Корпус 4",
        floors: 5,
        wings: [
          [120, 138, 345, 190],
          [120, 190, 165, 330],
          [250, 190, 290, 285],
        ],
      },
      { id: "5", name: "Корпус 5", floors: 4, wings: [[345, 138, 410, 190]] },
      { id: "6", name: "Корпус 6", floors: 5, wings: [[445, 150, 700, 205], [630, 205, 700, 245]] },
      { id: "7", name: "Корпус 7", floors: 5, wings: [[795, 150, 1035, 205], [795, 205, 850, 245]] },
      {
        id: "8",
        name: "Корпус 8",
        floors: 7,
        wings: [
          [975, 245, 1030, 470],
          [1100, 150, 1160, 470],
          [1030, 290, 1100, 340],
        ],
      },
      { id: "9", name: "Корпус 9", floors: 7, wings: [[960, 490, 1160, 530], [1040, 530, 1160, 580]] },
      { id: "kpp", name: "КПП", label: "КПП", floors: 1, wings: [[700, 200, 795, 235]] },
      { id: "sport", name: "Спортзал (вход с улицы)", label: "Спортзал", floors: 2, wings: [[285, 488, 385, 528]] },
    ],
    bridges: [
      { from: "5", to: "6", floors: [3], rect: [410, 158, 447, 190] },
      { from: "6", to: "2", floors: [2], rect: [468, 205, 517, 285] },
      { from: "4", to: "2", floors: [3], rect: [290, 288, 365, 330] },
      { from: "4", to: "3", floors: [3], rect: [123, 330, 163, 385] },
      { from: "2", to: "1", floors: [2], rect: [520, 418, 562, 470] },
      { from: "1", to: "8", floors: [2], rect: [935, 360, 977, 420] },
      { from: "1", to: "9", floors: [2], rect: [935, 470, 962, 495] },
      { from: "7", to: "8", floors: [1, 2], rect: [977, 205, 1033, 245] },
      { from: "7", to: "8", floors: [2, 3], rect: [1035, 150, 1100, 205] },
      { from: "8", to: "9", floors: [3, 6], rect: [1102, 470, 1160, 490] },
    ],
    rooms: [
      { building: "1", number: "125", floor: 1, label: "Медпункт", at: [912, 465] },
      { building: "1", number: "129", floor: 1, label: "Профком студентов", at: [912, 512] },
    ],
    places: [
      { kind: "cafe", building: "2", floor: 2, label: "Буфет", at: [490, 322] },
      { kind: "cafe", building: "3", floor: 2, label: "Буфет", at: [240, 503] },
      { kind: "cafe", building: "4", floor: 1, label: "Буфет", at: [320, 165] },
      { kind: "cafe", building: "6", floor: 2, label: "Буфет", at: [665, 178] },
      { kind: "cafe", building: "8", floor: 2, label: "Буфет", at: [1128, 368] },
      { kind: "place", building: "6", floor: 1, label: "Банкомат", at: [636, 232] },
      { kind: "place", building: "7", floor: 1, label: "Библиотека", at: [843, 232] },
      { kind: "place", building: "3", floor: 3, label: "Актовый зал", at: [285, 368] },
      { kind: "place", building: "3", floor: 3, label: "Кафедра физ. воспитания", at: [178, 505] },
      { kind: "place", building: "1", floor: 2, label: "Бухгалтерия", at: [595, 470] },
      { kind: "place", building: "1", floor: 3, label: "Кафедра иностр. языков", at: [595, 515] },
    ],
    entrances: [
      { building: "1", at: [745, 405], dir: "down", main: true },
      { building: "4", at: [322, 138], dir: "down" },
      { building: "4", at: [322, 190], dir: "up" },
      { building: "6", at: [665, 245], dir: "up" },
      { building: "7", at: [825, 245], dir: "up" },
      { building: "2", at: [525, 308], dir: "left" },
      { building: "3", at: [120, 415], dir: "right" },
      { building: "3", at: [145, 530], dir: "up" },
      { building: "sport", at: [385, 508], dir: "left" },
      { building: "9", at: [995, 530], dir: "up" },
      { building: "8", at: [1160, 315], dir: "left" },
      { building: "kpp", at: [747, 200], dir: "down" },
    ],
    streets: [
      { name: "ул. Карла Маркса", rect: [20, 30, 1280, 72] },
      { name: "ул. Пушкина", rect: [20, 72, 65, 620] },
      { name: "ул. Коммунистическая", rect: [1235, 72, 1280, 620] },
    ],
  },
  {
    // ЗАГЛУШКА: реальной схемы кампуса БашГУ пока нет
    id: "bashgu",
    title: "Кампус БашГУ",
    address: "ул. Заки Валиди, 32",
    scale: 0.4,
    buildings: [
      { id: "ф1", name: "Главный корпус", floors: 5, wings: [[440, 300, 840, 350]] },
      { id: "ф2", name: "Физмат корпус", floors: 5, wings: [[440, 350, 490, 520]] },
      { id: "ф3", name: "Гуманитарный корпус", floors: 6, wings: [[790, 350, 840, 520]] },
      { id: "ф4", name: "Библиотека", floors: 3, wings: [[560, 430, 720, 500]] },
    ],
    bridges: [],
    rooms: [],
    places: [],
    entrances: [{ building: "ф1", at: [640, 300], dir: "down", main: true }],
    streets: [{ name: "ул. Заки Валиди", rect: [300, 240, 980, 280] }],
  },
];

export const DEFAULT_CAMPUS_ID = "ugatu";

/** Ищет корпус по id (номер из ИСУ); кампус УГАТУ - первым, ИСУ нумерует по нему. */
export function findBuilding(buildingId: string): { campus: Campus; building: Building } | null {
  for (const campus of CAMPUSES) {
    const building = campus.buildings.find((item) => item.id === buildingId);
    if (building) return { campus, building };
  }
  return null;
}

/** Центр схемы кампуса в пикселях - сцена строится вокруг него. */
export function campusOrigin(campus: Campus): Point {
  const rects = campus.buildings.flatMap((b) => b.wings);
  const xs = rects.flatMap((r) => [r[0], r[2]]);
  const ys = rects.flatMap((r) => [r[1], r[3]]);
  return [(Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2];
}

/** Пиксели схемы -> метры сцены (x - вправо по схеме, z - вниз по схеме). */
export function toMeters(campus: Campus, [px, py]: Point): Point {
  const [ox, oy] = campusOrigin(campus);
  return [(px - ox) * campus.scale, (py - oy) * campus.scale];
}

/** Прямоугольник схемы -> центр и размеры в метрах. */
export function rectToMeters(campus: Campus, rect: Rect) {
  const [x1, z1] = toMeters(campus, [rect[0], rect[1]]);
  const [x2, z2] = toMeters(campus, [rect[2], rect[3]]);
  return { x: (x1 + x2) / 2, z: (z1 + z2) / 2, w: Math.abs(x2 - x1), d: Math.abs(z2 - z1) };
}
