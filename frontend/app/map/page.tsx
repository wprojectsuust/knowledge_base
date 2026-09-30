"use client";

import { useState } from "react";
import { CampusMap, type CampusTarget } from "@/components/campus/CampusMap";
import { buildRoute, type Route } from "@/lib/api";
import { DEFAULT_CAMPUS_ID, findBuilding, useCampuses } from "@/lib/campus-data";

/** "7-404", "кабинет 3-106б" -> корпус + кабинет; этаж - первая цифра кабинета. */
function parseRoomQuery(query: string): CampusTarget | null {
  const match = query.trim().match(/(\S+?)\s*-\s*(\d{3}[а-яa-z]?)$/i);
  if (!match) return null;
  return { building: match[1], room: match[2].toLowerCase(), floor: Number(match[2][0]) };
}

export default function MapPage() {
  const { campuses } = useCampuses();
  const [campusId, setCampusId] = useState(DEFAULT_CAMPUS_ID);
  const [target, setTarget] = useState<CampusTarget | null>(null);
  const [route, setRoute] = useState<Route | null>(null);
  const [source, setSource] = useState("");
  const [destination, setDestination] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const campus = campuses?.find((item) => item.id === campusId) ?? null;
  const building = target && campus ? campus.buildings.find((item) => item.id === target.building) ?? null : null;

  function focusOn(next: CampusTarget | null) {
    setRoute(null);
    setError(null);
    setTarget(next);
  }

  async function navigate(event: React.FormEvent) {
    event.preventDefault();
    if (!destination.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const result = await buildRoute(source.trim() || null, destination.trim());
      setCampusId(result.campus);
      setTarget(null);
      setRoute(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось построить маршрут");
    } finally {
      setBusy(false);
    }
  }

  function locate() {
    const parsed = parseRoomQuery(destination) ?? { building: destination.trim() };
    const found = campuses ? findBuilding(campuses, parsed.building) : null;
    if (!found) {
      setError("Не нашёл такой корпус или кабинет");
      return;
    }
    setCampusId(found.campus.id);
    focusOn(parsed);
  }

  return (
    <section className="map-page">
      <form className="map-toolbar map-nav" onSubmit={navigate}>
        <input
          value={source}
          onChange={(event) => setSource(event.target.value)}
          placeholder="Откуда (по умолчанию КПП)"
          aria-label="Откуда"
        />
        <span className="map-nav-arrow">→</span>
        <input
          value={destination}
          onChange={(event) => setDestination(event.target.value)}
          placeholder="Куда: 7-404, 1-125, 3…"
          aria-label="Куда"
        />
        <button type="submit" className="chip active" disabled={busy}>
          {busy ? "Строю…" : "Маршрут"}
        </button>
        <button type="button" className="chip" onClick={locate}>
          Показать
        </button>
        {error && <span className="map-error">{error}</span>}
      </form>

      <div className="map-toolbar">
        {campuses?.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`chip${item.id === campusId ? " active" : ""}`}
            onClick={() => {
              setCampusId(item.id);
              focusOn(null);
            }}
          >
            {item.title}
          </button>
        ))}
        <span className="map-divider" />
        <button type="button" className={`chip${building || route ? "" : " active"}`} onClick={() => focusOn(null)}>
          Весь кампус
        </button>
        {campus?.buildings.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`chip${item.id === building?.id ? " active" : ""}`}
            onClick={() => focusOn({ building: item.id })}
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
              onClick={() => focusOn({ building: building.id, floor: number === target?.floor ? null : number })}
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
          route={route}
          focused={building !== null || route !== null}
          onSelectBuilding={(id) => focusOn({ building: id })}
        />
        {route && (
          <ol className="map-steps">
            {route.steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
            <li className="map-steps-total">
              ≈{Math.round(route.distance_m)} м · {route.minutes} мин
            </li>
            {route.alternative && (
              <li className="map-steps-total map-steps-street">
                По улице (пунктир): ≈{Math.round(route.alternative.distance_m)} м · {route.alternative.minutes} мин
              </li>
            )}
          </ol>
        )}
      </div>

      <p className="map-hint">
        Янтарные блоки — лестницы, голубые — переходы, фиолетовый — подземный переход под КПП; маршрут ведёт
        тёплыми переходами, уличный вариант — янтарным пунктиром. Вращайте мышью или пальцем, колесо или щипок — масштаб, клик по
        корпусу — перелёт к нему, этаж — открыть его с кабинетами. Корпуса и переходы — по схеме UUST MAPS; этажность и раскладка
        кабинетов пока примерные.
      </p>
    </section>
  );
}
