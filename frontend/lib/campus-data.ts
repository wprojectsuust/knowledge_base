/**
 * Данные для 3D-карты кампусов. Сцена целиком строится из этого файла, так что после обхода
 * достаточно поправить цифры здесь, код трогать не нужно.
 *
 * ВНИМАНИЕ: расположение, размеры и этажность ниже - ПРИМЕРНЫЕ заглушки для прототипа.
 *
 * Система координат - метры: x растёт на восток, z - на юг, начало координат - условный
 * центр кампуса. Корпус - прямоугольник w (по x) × d (по z) с центром в (x, z), повёрнутый на
 * rotation градусов, высотой floors этажей.
 */

export type Room = {
  /** номер кабинета без корпуса, как в расписании: "404", "106б" */
  number: string;
  floor: number;
  /** положение внутри этажа в долях от размера корпуса: 0..1 по x и z */
  u: number;
  v: number;
};

export type Building = {
  /** как в ИСУ/расписании: "Корпус 7" -> id "7" */
  id: string;
  name: string;
  x: number;
  z: number;
  w: number;
  d: number;
  rotation?: number;
  floors: number;
  rooms?: Room[];
};

export type Bridge = {
  from: string;
  to: string;
  /** на каком этаже переход (1 - наземный) */
  floor: number;
};

export type Campus = {
  id: string;
  title: string;
  address: string;
  buildings: Building[];
  bridges: Bridge[];
};

export const FLOOR_HEIGHT = 4;

export const CAMPUSES: Campus[] = [
  {
    id: "ugatu",
    title: "Кампус УГАТУ",
    address: "ул. Карла Маркса, 12",
    buildings: [
      { id: "1", name: "Главный корпус", x: 0, z: 0, w: 70, d: 18, floors: 5 },
      { id: "2", name: "Корпус 2", x: -52, z: 22, w: 18, d: 44, floors: 4 },
      { id: "3", name: "Корпус 3", x: 50, z: 24, w: 18, d: 46, floors: 5 },
      { id: "4", name: "Корпус 4", x: 0, z: 50, w: 56, d: 16, floors: 4 },
      { id: "5", name: "Корпус 5", x: -60, z: 78, w: 40, d: 18, floors: 5 },
      { id: "6", name: "Корпус 6", x: 58, z: 80, w: 40, d: 18, floors: 6 },
      { id: "7", name: "Корпус 7", x: 0, z: 104, w: 60, d: 20, floors: 5 },
      { id: "8", name: "Корпус 8", x: -94, z: 30, w: 16, d: 40, floors: 4 },
      { id: "9", name: "Корпус 9", x: 96, z: 34, w: 16, d: 44, floors: 9 },
      { id: "10", name: "Корпус 10", x: 104, z: 106, w: 24, d: 24, floors: 4 },
    ],
    bridges: [
      { from: "1", to: "2", floor: 2 },
      { from: "1", to: "3", floor: 2 },
      { from: "2", to: "4", floor: 3 },
      { from: "3", to: "4", floor: 3 },
      { from: "4", to: "7", floor: 2 },
      { from: "5", to: "7", floor: 2 },
      { from: "6", to: "7", floor: 2 },
      { from: "2", to: "8", floor: 1 },
      { from: "3", to: "9", floor: 1 },
    ],
  },
  {
    id: "bashgu",
    title: "Кампус БашГУ",
    address: "ул. Заки Валиди, 32",
    buildings: [
      { id: "ф1", name: "Главный корпус", x: 0, z: 0, w: 80, d: 20, floors: 5 },
      { id: "ф2", name: "Физмат корпус", x: -50, z: 44, w: 20, d: 50, floors: 5 },
      { id: "ф3", name: "Корпус гуманитарных факультетов", x: 50, z: 44, w: 20, d: 50, floors: 6 },
      { id: "ф4", name: "Библиотека", x: 0, z: 70, w: 40, d: 24, floors: 3 },
    ],
    bridges: [
      { from: "ф1", to: "ф2", floor: 2 },
      { from: "ф1", to: "ф3", floor: 2 },
    ],
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
