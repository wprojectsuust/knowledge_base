"use client";

import { useState } from "react";
import { CampusMap, type CampusTarget } from "@/components/campus/CampusMap";
import { CAMPUSES, DEFAULT_CAMPUS_ID, findBuilding } from "@/lib/campus-data";

/** "7-404", "кабинет 3-106б" -> корпус + кабинет; этаж - первая цифра кабинета. */
function parseRoomQuery(query: string): CampusTarget | null {
  const match = query.trim().match(/(\S+?)\s*-\s*(\d{3}[а-яa-z]?)$/i);
  if (!match) return null;
  return { building: match[1], room: match[2].toLowerCase(), floor: Number(match[2][0]) };
}

export default function MapPage() {
  const [campusId, setCampusId] = useState(DEFAULT_CAMPUS_ID);
  const [target, setTarget] = useState<CampusTarget | null>(null);
  const [query, setQuery] = useState("");
  const [queryError, setQueryError] = useState(false);

  const campus = CAMPUSES.find((item) => item.id === campusId)!;
  const building = target ? campus.buildings.find((item) => item.id === target.building) ?? null : null;

  function selectBuilding(id: string | null) {
    setTarget(id ? { building: id } : null);
  }

  function searchRoom(event: React.FormEvent) {
    event.preventDefault();
    const parsed = parseRoomQuery(query);
    const found = parsed ? findBuilding(parsed.building) : null;
    setQueryError(!found);
    if (!parsed || !found) return;
    setCampusId(found.campus.id);
    setTarget(parsed);
  }

  return (
    <section className="map-page">
      <div className="map-toolbar">
        {CAMPUSES.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`chip${item.id === campusId ? " active" : ""}`}
            onClick={() => {
              setCampusId(item.id);
              selectBuilding(null);
            }}
          >
            {item.title} · {item.address}
          </button>
        ))}
        <form className="map-search" onSubmit={searchRoom}>
          <input
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setQueryError(false);
            }}
            placeholder="Кабинет, напр. 7-404"
            aria-invalid={queryError}
            style={queryError ? { borderColor: "#ff9a94" } : undefined}
          />
          <button type="submit" className="chip">
            Найти
          </button>
        </form>
      </div>

      <div className="map-toolbar">
        <button type="button" className={`chip${building ? "" : " active"}`} onClick={() => selectBuilding(null)}>
          Весь кампус
        </button>
        {campus.buildings.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`chip${item.id === building?.id ? " active" : ""}`}
            onClick={() => selectBuilding(item.id)}
            title={item.name}
          >
            {item.label ?? item.id}
          </button>
        ))}
      </div>

      {building && (
        <div className="map-toolbar">
          {Array.from({ length: building.floors }, (_, index) => index + 1).map((number) => (
            <button
              key={number}
              type="button"
              className={`chip${number === target?.floor ? " active" : ""}`}
              onClick={() =>
                setTarget({ building: building.id, floor: number === target?.floor ? null : number })
              }
            >
              {number} этаж
            </button>
          ))}
        </div>
      )}

      <div className="map-stage">
        <CampusMap
          campusId={campusId}
          target={target}
          focused={building !== null}
          onSelectBuilding={selectBuilding}
        />
      </div>

      <p className="map-hint">
        Крутите мышью, колесо — масштаб, клик по корпусу — перелёт к нему, этаж — открыть его с кабинетами. Корпуса
        и переходы — по схеме UUST MAPS; этажность и раскладка кабинетов пока примерные.
      </p>
    </section>
  );
}
