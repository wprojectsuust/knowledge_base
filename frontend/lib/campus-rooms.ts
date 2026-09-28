import { rectToMeters, toMeters, type Building, type Campus } from "@/lib/campus-data";

export type RoomCell = {
  number: string;
  floor: number;
  /** центр и размеры в метрах сцены */
  x: number;
  z: number;
  w: number;
  d: number;
  label?: string;
};

const ROOM_LENGTH = 6; // метров вдоль коридора на один кабинет
const CORRIDOR = 2.4;
const TWO_ROWS_MIN_WIDTH = 10; // уже этого - кабинеты в один ряд, без коридора посередине
const GAP = 0.35; // зазор между кабинетами, чтобы на карте читались стены

/**
 * Раскладывает кабинеты по этажам корпуса: в каждом крыле коридор по длинной оси, кабинеты по
 * обе стороны, нумерация «этаж + порядковый номер» (4-й этаж -> 401, 402, ...), как в ИСУ.
 *
 * Раскладка ПРИБЛИЗИТЕЛЬНАЯ (реальных планов этажей нет), но известные кабинеты из данных
 * (медпункт 1-125 и т.п.) ставятся точно на своё место.
 */
export function buildingRooms(campus: Campus, building: Building): RoomCell[] {
  const cells: RoomCell[] = [];

  for (let floor = 1; floor <= building.floors; floor += 1) {
    let counter = 1;
    for (const wing of building.wings) {
      const { x, z, w, d } = rectToMeters(campus, wing);
      const alongX = w >= d;
      const long = alongX ? w : d;
      const short = alongX ? d : w;
      const count = Math.max(1, Math.floor(long / ROOM_LENGTH));
      const length = long / count;
      const rows = short >= TWO_ROWS_MIN_WIDTH ? 2 : 1;
      const rowDepth = rows === 2 ? (short - CORRIDOR) / 2 : short;

      for (let row = 0; row < rows; row += 1) {
        const across = rows === 2 ? (row === 0 ? -1 : 1) * (CORRIDOR / 2 + rowDepth / 2) : 0;
        for (let i = 0; i < count; i += 1) {
          const along = -long / 2 + (i + 0.5) * length;
          cells.push({
            number: `${floor}${String(counter).padStart(2, "0")}`,
            floor,
            x: x + (alongX ? along : across),
            z: z + (alongX ? across : along),
            w: (alongX ? length : rowDepth) - GAP,
            d: (alongX ? rowDepth : length) - GAP,
          });
          counter += 1;
        }
      }
    }
  }

  for (const known of campus.rooms.filter((room) => room.building === building.id)) {
    const [kx, kz] = toMeters(campus, known.at);
    const onFloor = cells.filter((cell) => cell.floor === known.floor);
    const cell =
      onFloor.find((c) => Math.abs(c.x - kx) <= c.w / 2 && Math.abs(c.z - kz) <= c.d / 2) ??
      onFloor.reduce<RoomCell | null>(
        (best, c) => (!best || Math.hypot(c.x - kx, c.z - kz) < Math.hypot(best.x - kx, best.z - kz) ? c : best),
        null,
      );
    if (!cell) continue;
    // номер уже занят автораскладкой - меняемся номерами, чтобы не было дублей
    const clash = onFloor.find((c) => c !== cell && c.number === known.number);
    if (clash) clash.number = cell.number;
    cell.number = known.number;
    cell.label = known.label;
  }

  return cells;
}

export function findRoom(cells: RoomCell[], number: string, floor?: number | null): RoomCell | null {
  const normalized = number.toLowerCase();
  return (
    cells.find((cell) => cell.number.toLowerCase() === normalized && (!floor || cell.floor === floor)) ??
    // "106б" - буквы в автораскладке нет, ищем по цифрам
    cells.find((cell) => cell.number === normalized.replace(/\D+$/, "") && (!floor || cell.floor === floor)) ??
    null
  );
}
