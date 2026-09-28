"use client";

import { useEffect, useState } from "react";
import { CampusMap } from "@/components/campus/CampusMap";
import type { Location } from "@/lib/api";

type Phase = "hidden" | "corner" | "center" | "mini";

type VenueMapProps = {
  location: Location;
  /** Когда true (ответ допечатан) - окно карты выезжает из угла в центр. */
  ready: boolean;
  onDismiss: () => void;
};

function describe(location: Location) {
  const parts = [`Корпус ${location.building}`];
  if (location.room) parts.push(`кабинет ${location.building}-${location.room}`);
  if (location.floor) parts.push(`${location.floor} этаж`);
  return parts;
}

/**
 * Окно карты с «перелётом»: появляется маленьким в правом нижнем углу, пока ИИ печатает ответ,
 * затем плавно выезжает в центр экрана и показывает точку. Закрытие сворачивает обратно в угол.
 * В углу кампус медленно облетается целиком, в центре камера летит к нужному корпусу и
 * раскрывает этажи (см. CampusScene).
 */
export function VenueMap({ location, ready, onDismiss }: VenueMapProps) {
  const [phase, setPhase] = useState<Phase>("hidden");

  useEffect(() => {
    // следующий кадр, чтобы сработал transition из hidden
    const frame = requestAnimationFrame(() => setPhase("corner"));
    return () => cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    if (!ready) return;
    const timer = setTimeout(() => setPhase((prev) => (prev === "corner" ? "center" : prev)), 350);
    return () => clearTimeout(timer);
  }, [ready]);

  useEffect(() => {
    if (phase !== "center") return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setPhase("mini");
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [phase]);

  const [title, ...details] = describe(location);
  const expanded = phase === "center";

  return (
    <>
      <div className={`venue-backdrop${expanded ? " visible" : ""}`} onClick={() => setPhase("mini")} />
      <div
        className={`venue-map phase-${phase}`}
        role={expanded ? "dialog" : "button"}
        aria-label={`Карта: ${describe(location).join(", ")}`}
        onClick={() => !expanded && setPhase("center")}
      >
        <div className="venue-canvas">
          {phase !== "hidden" && <CampusMap target={location} focused={expanded} interactive={expanded} />}
        </div>

        <div className="venue-label">
          <p className="venue-title">{title}</p>
          {details.length > 0 && <p className="venue-details">{details.join(" · ")}</p>}
        </div>

        {expanded && <p className="venue-stub">Расположение корпусов пока примерное · крутите мышью</p>}

        <button
          type="button"
          className="venue-close"
          aria-label={expanded ? "Свернуть карту" : "Закрыть карту"}
          onClick={(event) => {
            event.stopPropagation();
            if (expanded) setPhase("mini");
            else onDismiss();
          }}
        >
          ×
        </button>
      </div>
    </>
  );
}
