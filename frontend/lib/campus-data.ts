"use client";

import { useEffect, useState } from "react";
import { apiUrl } from "@/lib/api";

/**
 * Данные кампусов приходят с бэкенда (GET /campus) - там же строятся маршруты, так что
 * источник правды один: backend/src/repositories/campus.json.
 *
 * Координаты - пиксели схемы кампуса, прямоугольник [x1, y1, x2, y2]; scale - метров в пикселе.
 */

export type Rect = [number, number, number, number];
export type Point = [number, number];
export type Direction = "up" | "down" | "left" | "right";

export type Building = { id: string; name: string; label: string | null; floors: number; wings: Rect[] };
export type Bridge = { from: string; to: string; floors: number[]; rect: Rect };
export type Stairs = { building: string; at: Point };
export type Place = { id: string; kind: "cafe" | "place"; building: string; floor: number; label: string; at: Point };
export type Entrance = { building: string; at: Point; dir: Direction };
export type Street = { name: string; rect: Rect };
/** [номер, этаж, x1, y1, x2, y2, подпись|null] - компактно, кабинетов тысячи */
export type RawRoom = [string, number, number, number, number, number, string | null];

export type Campus = {
  id: string;
  title: string;
  address: string;
  scale: number;
  buildings: Building[];
  bridges: Bridge[];
  stairs: Stairs[];
  places: Place[];
  entrances: Entrance[];
  streets: Street[];
  rooms: Record<string, RawRoom[]>;
};

export const FLOOR_HEIGHT = 4;
export const DEFAULT_CAMPUS_ID = "ugatu";

let campusesPromise: Promise<Campus[]> | null = null;

function fetchCampuses(): Promise<Campus[]> {
  campusesPromise ??= fetch(apiUrl("/campus"))
    .then((response) => {
      if (!response.ok) throw new Error(`Сервер ответил ${response.status}`);
      return response.json() as Promise<Campus[]>;
    })
    .catch((error) => {
      campusesPromise = null; // дать шанс повторить
      throw error;
    });
  return campusesPromise;
}

/** Данные кампусов, загружаются один раз на вкладку. */
export function useCampuses() {
  const [campuses, setCampuses] = useState<Campus[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    fetchCampuses()
      .then((data) => alive && setCampuses(data))
      .catch((err: unknown) => alive && setError(err instanceof Error ? err.message : "Не удалось загрузить карту"));
    return () => {
      alive = false;
    };
  }, []);

  return { campuses, error };
}

export function findBuilding(campuses: Campus[], buildingId: string) {
  for (const campus of campuses) {
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
