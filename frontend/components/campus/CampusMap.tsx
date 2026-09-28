"use client";

import dynamic from "next/dynamic";

/**
 * Three.js тяжёлый и работает только в браузере - грузим сцену лениво, без SSR, и только
 * когда карта реально показывается.
 */
export const CampusMap = dynamic(() => import("@/components/campus/CampusScene"), {
  ssr: false,
  loading: () => <div className="campus-loading">Загружаю 3D-карту…</div>,
});

export type { CampusTarget } from "@/components/campus/CampusScene";
