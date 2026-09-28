"use client";

import { useState } from "react";
import { CampusMap } from "@/components/campus/CampusMap";
import { CAMPUSES, DEFAULT_CAMPUS_ID } from "@/lib/campus-data";

export default function MapPage() {
  const [campusId, setCampusId] = useState(DEFAULT_CAMPUS_ID);
  const [buildingId, setBuildingId] = useState<string | null>(null);
  const [floor, setFloor] = useState<number | null>(null);

  const campus = CAMPUSES.find((item) => item.id === campusId)!;
  const building = campus.buildings.find((item) => item.id === buildingId) ?? null;

  function selectBuilding(id: string | null) {
    setBuildingId(id);
    setFloor(null);
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
      </div>

      <div className="map-toolbar">
        <button type="button" className={`chip${building ? "" : " active"}`} onClick={() => selectBuilding(null)}>
          Весь кампус
        </button>
        {campus.buildings.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`chip${item.id === buildingId ? " active" : ""}`}
            onClick={() => selectBuilding(item.id)}
            title={item.name}
          >
            {item.id}
          </button>
        ))}
      </div>

      {building && (
        <div className="map-toolbar">
          {Array.from({ length: building.floors }, (_, index) => index + 1).map((number) => (
            <button
              key={number}
              type="button"
              className={`chip${number === floor ? " active" : ""}`}
              onClick={() => setFloor(number === floor ? null : number)}
            >
              {number} этаж
            </button>
          ))}
        </div>
      )}

      <div className="map-stage">
        <CampusMap
          campusId={campusId}
          target={building ? { building: building.id, floor } : null}
          focused={building !== null}
          onSelectBuilding={selectBuilding}
        />
      </div>

      <p className="map-hint">
        Крутите мышью, колесо — масштаб, клик по корпусу — перелёт к нему. Расположение корпусов пока примерное.
      </p>
    </section>
  );
}
