"use client";

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { CameraControls, Edges, Grid, Html, Line } from "@react-three/drei";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import * as THREE from "three";
import type { Line2 } from "three-stdlib";
import {
  DEFAULT_CAMPUS_ID,
  FLOOR_HEIGHT,
  rectToMeters,
  toMeters,
  useCampuses,
  type Building,
  type Campus,
  type Direction,
} from "@/lib/campus-data";
import type { Route } from "@/lib/api";

export type CampusTarget = {
  building: string;
  room?: string | null;
  floor?: number | null;
};

type CampusSceneProps = {
  campusId?: string;
  target?: CampusTarget | null;
  /** маршрут от бэкенда - если есть, рисуется вместо фокуса на цели */
  route?: Route | null;
  /** true - камера летит к цели/маршруту; false - медленный облёт всего кампуса */
  focused: boolean;
  /** можно ли крутить сцену мышью (в мини-окне в углу - нет) */
  interactive?: boolean;
  onSelectBuilding?: (id: string) => void;
};

const SLAB = FLOOR_HEIGHT * 0.82; // толщина плиты этажа - между плитами видны щели
const LIFT = 26; // на сколько поднимаются этажи над нужным, чтобы открыть его сверху
const EXPLODE_GAP = 5; // раздвижка этажей, когда выбран корпус без этажа

const BODY = new THREE.Color("#2f4dff");
const EDGE = { normal: "#6f8bff", dim: "#1c2a70", bright: "#c9d6ff" };
const ROOM_COLOR = new THREE.Color("#4a66ff");
const KNOWN_ROOM_COLOR = new THREE.Color("#38c6ff");

type Box = { x: number; z: number; w: number; d: number };
type RoomCell = Box & { number: string; floor: number; label: string | null };

function boundsOf(boxes: Box[]) {
  const minX = Math.min(...boxes.map((b) => b.x - b.w / 2));
  const maxX = Math.max(...boxes.map((b) => b.x + b.w / 2));
  const minZ = Math.min(...boxes.map((b) => b.z - b.d / 2));
  const maxZ = Math.max(...boxes.map((b) => b.z + b.d / 2));
  return { x: (minX + maxX) / 2, z: (minZ + maxZ) / 2, w: maxX - minX, d: maxZ - minZ };
}

/** Плавно ведёт число к цели независимо от FPS. */
function approach(current: number, target: number, delta: number, speed = 4) {
  return current + (target - current) * (1 - Math.exp(-delta * speed));
}

function roomsOf(campus: Campus, buildingId: string): RoomCell[] {
  return (campus.rooms[buildingId] ?? []).map(([number, floor, x1, y1, x2, y2, label]) => ({
    number,
    floor,
    label,
    ...rectToMeters(campus, [x1, y1, x2, y2]),
  }));
}

function findRoom(cells: RoomCell[], number: string, floor?: number | null) {
  const lowered = number.toLowerCase();
  const digits = lowered.replace(/\D+$/, "");
  const onFloor = (cell: RoomCell) => !floor || cell.floor === floor;
  return (
    cells.find((cell) => cell.number === lowered && onFloor(cell)) ??
    cells.find((cell) => cell.number === digits && onFloor(cell)) ??
    null
  );
}

type FloorMode = "normal" | "dimmed" | "target" | "below" | "above" | "route";

const FLOOR_LOOK: Record<FloorMode, { opacity: number; edge: string }> = {
  normal: { opacity: 0.3, edge: EDGE.normal },
  dimmed: { opacity: 0.05, edge: EDGE.dim },
  target: { opacity: 0.1, edge: EDGE.bright },
  below: { opacity: 0.1, edge: EDGE.normal },
  above: { opacity: 0.025, edge: EDGE.dim },
  route: { opacity: 0.08, edge: EDGE.normal },
};

function Floor({
  wings,
  index,
  mode,
  lift,
  onClick,
  children,
}: {
  wings: Box[];
  index: number;
  mode: FloorMode;
  lift: number;
  onClick?: () => void;
  children?: React.ReactNode;
}) {
  const group = useRef<THREE.Group>(null);
  // один материал на весь этаж - меньше объектов и одна анимация прозрачности
  const material = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: BODY,
        emissive: BODY,
        emissiveIntensity: 0.35,
        transparent: true,
        opacity: FLOOR_LOOK.normal.opacity,
        depthWrite: false,
      }),
    [],
  );
  useEffect(() => () => material.dispose(), [material]);

  const look = FLOOR_LOOK[mode];
  const baseY = index * FLOOR_HEIGHT;

  useFrame((_, delta) => {
    if (!group.current) return;
    group.current.position.y = approach(group.current.position.y, baseY + lift, delta);
    material.opacity = approach(material.opacity, look.opacity, delta);
  });

  return (
    <group ref={group} position={[0, baseY, 0]}>
      {wings.map((wing, i) => (
        <mesh
          key={i}
          position={[wing.x, SLAB / 2, wing.z]}
          material={material}
          onClick={
            onClick
              ? (event) => {
                  event.stopPropagation();
                  onClick();
                }
              : undefined
          }
        >
          <boxGeometry args={[wing.w, SLAB, wing.d]} />
          <Edges color={look.edge} />
        </mesh>
      ))}
      {children}
    </group>
  );
}

/** Кабинеты этажа - отдельные объекты: один InstancedMesh на этаж (один draw call на сотню кабинетов). */
function RoomsLayer({
  cells,
  highlight,
  showLabels,
}: {
  cells: RoomCell[];
  highlight: RoomCell | null;
  showLabels: boolean;
}) {
  const mesh = useRef<THREE.InstancedMesh>(null);

  useLayoutEffect(() => {
    const instanced = mesh.current;
    if (!instanced) return;
    const dummy = new THREE.Object3D();
    cells.forEach((cell, i) => {
      dummy.position.set(cell.x, SLAB * 0.45, cell.z);
      dummy.scale.set(cell.w, SLAB * 0.7, cell.d);
      dummy.updateMatrix();
      instanced.setMatrixAt(i, dummy.matrix);
      instanced.setColorAt(i, cell.label ? KNOWN_ROOM_COLOR : ROOM_COLOR);
    });
    instanced.instanceMatrix.needsUpdate = true;
    if (instanced.instanceColor) instanced.instanceColor.needsUpdate = true;
  }, [cells]);

  return (
    <group>
      <instancedMesh key={cells.length} ref={mesh} args={[undefined, undefined, cells.length]}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial
          color="#ffffff"
          emissive="#1a2a90"
          emissiveIntensity={0.4}
          transparent
          opacity={0.5}
          depthWrite={false}
        />
      </instancedMesh>
      {highlight && (
        <mesh position={[highlight.x, SLAB * 0.55, highlight.z]}>
          <boxGeometry args={[highlight.w, SLAB * 1.1, highlight.d]} />
          <meshBasicMaterial color="#7ef0ff" transparent opacity={0.85} />
        </mesh>
      )}
      {showLabels &&
        cells
          .filter((cell) => cell.label && cell !== highlight)
          .map((cell) => (
            <Html key={cell.number} position={[cell.x, SLAB + 2, cell.z]} center zIndexRange={[10, 0]}>
              <span className="campus-place">
                {cell.label} · {cell.number}
              </span>
            </Html>
          ))}
    </group>
  );
}

/** Лестница на этаже - янтарный блок; стоит внутри группы этажа, поэтому «ездит» вместе с ним. */
function StairsBlock({ x, z }: { x: number; z: number }) {
  return (
    <mesh position={[x, SLAB / 2, z]}>
      <boxGeometry args={[3.2, SLAB * 1.02, 3.2]} />
      <meshStandardMaterial color="#ffb347" emissive="#ff9f1c" emissiveIntensity={0.6} transparent opacity={0.8} />
    </mesh>
  );
}

const ARROW_ROTATION: Record<Direction, number> = {
  // стрелка по умолчанию (конус, повёрнутый на бок) смотрит в -z = вверх по схеме
  up: 0,
  left: Math.PI / 2,
  down: Math.PI,
  right: -Math.PI / 2,
};

function EntranceArrow({ x, z, dir }: { x: number; z: number; dir: Direction }) {
  return (
    <group position={[x, 0.3, z]} rotation={[0, ARROW_ROTATION[dir], 0]}>
      {/* стрелка стоит перед входом и указывает в здание */}
      <mesh position={[0, 0, 5]} rotation={[-Math.PI / 2, 0, 0]}>
        <coneGeometry args={[2, 5, 3]} />
        <meshBasicMaterial color="#38c6ff" />
      </mesh>
    </group>
  );
}

function routeY(floor: number) {
  return floor === 0 ? 0.8 : (floor - 1) * FLOOR_HEIGHT + 1.4;
}

/** Маршрут: светящаяся линия с бегущим пунктиром поверх всего (depthTest off), старт и финиш. */
function RoutePath({ campus, route }: { campus: Campus; route: Route }) {
  const dashed = useRef<Line2>(null);
  const points = useMemo(
    () =>
      route.points.map((p) => {
        const [x, z] = toMeters(campus, [p.x, p.y]);
        return new THREE.Vector3(x, routeY(p.floor), z);
      }),
    [campus, route],
  );

  useFrame((_, delta) => {
    const material = dashed.current?.material as { dashOffset: number } | undefined;
    if (material) material.dashOffset -= delta * 8;
  });

  const start = points[0];
  const end = points[points.length - 1];
  const endPoint = route.points[route.points.length - 1];

  return (
    <group renderOrder={10}>
      <Line points={points} color="#38c6ff" lineWidth={9} transparent opacity={0.25} depthTest={false} />
      <Line
        ref={dashed}
        points={points}
        color="#bff6ff"
        lineWidth={3.5}
        dashed
        dashSize={3}
        gapSize={2}
        depthTest={false}
        transparent
      />
      <mesh position={start}>
        <sphereGeometry args={[1.8, 16, 16]} />
        <meshBasicMaterial color="#5cffb0" depthTest={false} transparent />
      </mesh>
      <Html position={[start.x, start.y + 5, start.z]} center zIndexRange={[10, 0]}>
        <span className="campus-route-start">{route.from_label}</span>
      </Html>
      <Html position={[end.x, end.y + 6, end.z]} center zIndexRange={[10, 0]}>
        <div className="campus-pin dropped">
          <span className="campus-pin-title">{route.to_label}</span>
          {endPoint.floor > 0 && <span className="campus-pin-sub">{endPoint.floor} этаж</span>}
        </div>
      </Html>
    </group>
  );
}

function CameraRig({
  controls,
  overview,
  focus,
}: {
  controls: React.RefObject<CameraControls | null>;
  overview: { w: number; d: number };
  focus: { x: number; z: number; w: number; d: number; y: number } | null;
}) {
  useEffect(() => {
    const cc = controls.current;
    if (!cc) return;
    if (focus) {
      // сверху-спереди (с юга по схеме), чтобы заглянуть в открытый этаж
      const distance = Math.max(focus.w, focus.d) * 0.9 + 45;
      void cc.setLookAt(
        focus.x + distance * 0.25,
        focus.y + distance * 0.95,
        focus.z + distance * 0.8,
        focus.x,
        focus.y,
        focus.z,
        true,
      );
    } else {
      const size = Math.max(overview.w, overview.d);
      void cc.setLookAt(size * 0.35, size * 0.55, size * 0.75, 0, 0, 0, true);
    }
  }, [controls, overview, focus]);

  useFrame((_, delta) => {
    // медленный облёт, пока ни на что не смотрим
    if (!focus) controls.current?.rotate(delta * 0.05, 0, true);
  });

  return null;
}

export default function CampusScene(props: CampusSceneProps) {
  const { campuses, error } = useCampuses();
  if (error) return <div className="campus-loading">Карта недоступна: {error}</div>;
  if (!campuses) return <div className="campus-loading">Загружаю 3D-карту…</div>;
  return <CampusCanvas campuses={campuses} {...props} />;
}

function CampusCanvas({
  campuses,
  campusId,
  target,
  route,
  focused,
  interactive = true,
  onSelectBuilding,
}: CampusSceneProps & { campuses: Campus[] }) {
  const campus: Campus = useMemo(() => {
    const byTarget = target ? campuses.find((c) => c.buildings.some((b) => b.id === target.building)) : undefined;
    const wanted = campusId ?? route?.campus ?? byTarget?.id ?? DEFAULT_CAMPUS_ID;
    return campuses.find((c) => c.id === wanted) ?? campuses[0];
  }, [campuses, campusId, target, route]);

  const wingsById = useMemo(
    () => new Map(campus.buildings.map((b) => [b.id, b.wings.map((rect) => rectToMeters(campus, rect))])),
    [campus],
  );
  const overview = useMemo(() => boundsOf([...wingsById.values()].flat()), [wingsById]);

  const showRoute = focused && route !== null && route !== undefined && route.campus === campus.id;
  const targetBuilding: Building | null =
    (!showRoute && target && campus.buildings.find((b) => b.id === target.building)) || null;
  const isFocused = focused && targetBuilding !== null;

  const rooms = useMemo(() => (targetBuilding ? roomsOf(campus, targetBuilding.id) : []), [campus, targetBuilding]);
  const targetRoom = target?.room ? findRoom(rooms, target.room, target.floor) : null;
  const targetFloor =
    targetRoom?.floor ?? (target?.floor ? Math.min(target.floor, targetBuilding?.floors ?? 1) : null);

  // этаж «открывается», когда камера уже почти долетела - так эффект читается
  const [opened, setOpened] = useState(false);
  useEffect(() => {
    setOpened(false);
    if (!isFocused) return;
    const timer = setTimeout(() => setOpened(true), 1000);
    return () => clearTimeout(timer);
  }, [isFocused, targetBuilding, targetFloor]);

  const focus = useMemo(() => {
    if (showRoute && route) {
      const boxes = route.points.map((p) => {
        const [x, z] = toMeters(campus, [p.x, p.y]);
        return { x, z, w: 0, d: 0 };
      });
      const maxFloor = Math.max(...route.points.map((p) => p.floor));
      return { ...boundsOf(boxes), y: routeY(maxFloor) / 2 };
    }
    if (!isFocused || !targetBuilding) return null;
    const b = boundsOf(wingsById.get(targetBuilding.id)!);
    const y = targetFloor ? (targetFloor - 1) * FLOOR_HEIGHT + SLAB : (targetBuilding.floors * FLOOR_HEIGHT) / 2;
    return { ...b, y };
  }, [showRoute, route, campus, isFocused, targetBuilding, targetFloor, wingsById]);

  const routeBuildings = useMemo(
    () => new Set(showRoute && route ? route.points.map((p) => p.building).filter(Boolean) : []),
    [showRoute, route],
  );

  const controls = useRef<CameraControls | null>(null);

  return (
    <Canvas camera={{ position: [260, 220, 340], fov: 38, near: 1, far: 3000 }} dpr={[1, 1.5]}>
      <color attach="background" args={["#050b24"]} />
      <fog attach="fog" args={["#050b24", 350, 1000]} />
      <ambientLight intensity={0.7} />
      <directionalLight position={[120, 260, 80]} intensity={1.1} />

      <Grid
        infiniteGrid
        cellSize={10}
        sectionSize={50}
        cellColor="#16235c"
        sectionColor="#2c45c4"
        cellThickness={0.6}
        sectionThickness={1}
        fadeDistance={800}
        fadeStrength={1.4}
        position={[0, -0.05, 0]}
      />

      {campus.streets.map((street) => {
        const s = rectToMeters(campus, street.rect);
        const alongX = s.w >= s.d;
        return (
          <group key={street.name}>
            <mesh position={[s.x, 0.02, s.z]} rotation={[-Math.PI / 2, 0, 0]}>
              <planeGeometry args={[s.w, s.d]} />
              <meshBasicMaterial color="#1a2a78" transparent opacity={isFocused ? 0.25 : 0.55} />
            </mesh>
            <Html position={[s.x, 1, s.z]} center zIndexRange={[10, 0]}>
              <span className={`campus-street${alongX ? "" : " vertical"}`}>{street.name}</span>
            </Html>
          </group>
        );
      })}

      {campus.bridges.map((bridge, i) => {
        const r = rectToMeters(campus, bridge.rect);
        return bridge.floors.map((floor) => (
          <mesh key={`${i}-${floor}`} position={[r.x, (floor - 1) * FLOOR_HEIGHT + SLAB / 2, r.z]}>
            <boxGeometry args={[r.w, SLAB * 0.7, r.d]} />
            <meshStandardMaterial
              color="#38c6ff"
              emissive="#38c6ff"
              emissiveIntensity={0.6}
              transparent
              opacity={isFocused ? 0.06 : 0.4}
              depthWrite={false}
            />
          </mesh>
        ));
      })}

      {campus.buildings.map((building) => {
        const wings = wingsById.get(building.id)!;
        const isTarget = building === targetBuilding;
        const top = boundsOf(wings);
        const stairs = campus.stairs.filter((s) => s.building === building.id).map((s) => toMeters(campus, s.at));
        const showStairs = (isTarget && opened) || routeBuildings.has(building.id);
        const buildingPlaces = isTarget && opened ? campus.places.filter((p) => p.building === building.id) : [];

        return (
          <group key={building.id}>
            {Array.from({ length: building.floors }, (_, index) => {
              const floor = index + 1;
              let mode: FloorMode = showRoute ? "route" : "normal";
              let lift = 0;
              if (isFocused && !isTarget) mode = "dimmed";
              if (isTarget && opened) {
                if (targetFloor === null) {
                  lift = index * EXPLODE_GAP;
                } else if (floor === targetFloor) {
                  mode = "target";
                } else if (floor > targetFloor) {
                  mode = "above";
                  lift = LIFT;
                } else {
                  mode = "below";
                }
              }
              const visibleFloor = targetFloor === null || floor <= targetFloor;
              const floorCells =
                isTarget && opened && visibleFloor ? rooms.filter((c) => c.floor === floor) : [];
              const floorPlaces = buildingPlaces.filter((p) => p.floor === floor && visibleFloor);

              return (
                <Floor
                  key={index}
                  wings={wings}
                  index={index}
                  mode={mode}
                  lift={lift}
                  onClick={interactive && onSelectBuilding ? () => onSelectBuilding(building.id) : undefined}
                >
                  {floorCells.length > 0 && (
                    <RoomsLayer
                      cells={floorCells}
                      highlight={targetRoom?.floor === floor ? targetRoom : null}
                      showLabels={floor === (targetFloor ?? 1)}
                    />
                  )}
                  {showStairs && (mode !== "above" || !isTarget) &&
                    stairs.map(([x, z], i) => <StairsBlock key={i} x={x} z={z} />)}
                  {floorPlaces.map((place) => {
                    const [x, z] = toMeters(campus, place.at);
                    return (
                      <Html key={place.id} position={[x, SLAB + 2, z]} center zIndexRange={[10, 0]}>
                        <span className={`campus-place${place.kind === "cafe" ? " cafe" : ""}`}>
                          {place.label} · {place.floor} эт.
                        </span>
                      </Html>
                    );
                  })}
                </Floor>
              );
            })}

            {!isFocused && (
              <Html position={[top.x, building.floors * FLOOR_HEIGHT + 4, top.z]} center zIndexRange={[10, 0]}>
                <span className="campus-label">{building.label ?? building.id}</span>
              </Html>
            )}

            {isTarget && (
              <Html
                position={[
                  targetRoom?.x ?? top.x,
                  targetFloor ? (targetFloor - 1) * FLOOR_HEIGHT + SLAB + 6 : building.floors * FLOOR_HEIGHT + 6,
                  targetRoom?.z ?? top.z,
                ]}
                center
                zIndexRange={[10, 0]}
              >
                <div className={`campus-pin${opened ? " dropped" : ""}`}>
                  <span className="campus-pin-title">
                    {target?.room ? `${building.id}-${target.room}` : building.name}
                  </span>
                  {targetFloor && (
                    <span className="campus-pin-sub">
                      {targetFloor} этаж{targetRoom?.label ? ` · ${targetRoom.label}` : ""}
                    </span>
                  )}
                </div>
              </Html>
            )}
          </group>
        );
      })}

      {campus.entrances
        .filter((entrance) => !isFocused || entrance.building === targetBuilding?.id)
        .map((entrance, i) => {
          const [x, z] = toMeters(campus, entrance.at);
          return <EntranceArrow key={i} x={x} z={z} dir={entrance.dir} />;
        })}

      {showRoute && route && <RoutePath campus={campus} route={route} />}

      <CameraControls
        ref={controls}
        enabled={interactive}
        smoothTime={0.9}
        minDistance={30}
        maxDistance={900}
        maxPolarAngle={Math.PI * 0.45}
      />
      <CameraRig controls={controls} overview={overview} focus={focus} />

      <EffectComposer multisampling={0}>
        <Bloom mipmapBlur luminanceThreshold={0.2} intensity={0.7} radius={0.6} />
      </EffectComposer>
    </Canvas>
  );
}
