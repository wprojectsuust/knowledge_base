"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { CameraControls, Edges, Grid, Html } from "@react-three/drei";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import * as THREE from "three";
import {
  CAMPUSES,
  DEFAULT_CAMPUS_ID,
  FLOOR_HEIGHT,
  rectToMeters,
  toMeters,
  type Building,
  type Campus,
  type Direction,
} from "@/lib/campus-data";
import { buildingRooms, findRoom, type RoomCell } from "@/lib/campus-rooms";

export type CampusTarget = {
  building: string;
  room?: string | null;
  floor?: number | null;
};

type CampusSceneProps = {
  campusId?: string;
  target?: CampusTarget | null;
  /** true - камера летит к цели и раскрывает этаж; false - медленный облёт всего кампуса */
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

type Box = { x: number; z: number; w: number; d: number };

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

type FloorMode = "normal" | "dimmed" | "target" | "below" | "above";

const FLOOR_LOOK: Record<FloorMode, { opacity: number; edge: string }> = {
  normal: { opacity: 0.3, edge: EDGE.normal },
  dimmed: { opacity: 0.05, edge: EDGE.dim },
  target: { opacity: 0.16, edge: EDGE.bright },
  below: { opacity: 0.12, edge: EDGE.normal },
  above: { opacity: 0.025, edge: EDGE.dim },
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

/** Кабинеты этажа: контуры одной геометрией (один draw call), нужный кабинет - светящийся блок. */
function RoomsLayer({ cells, highlight }: { cells: RoomCell[]; highlight: RoomCell | null }) {
  const geometry = useMemo(() => {
    const points: number[] = [];
    const y = SLAB + 0.05;
    for (const c of cells) {
      const x1 = c.x - c.w / 2;
      const x2 = c.x + c.w / 2;
      const z1 = c.z - c.d / 2;
      const z2 = c.z + c.d / 2;
      points.push(x1, y, z1, x2, y, z1, x2, y, z1, x2, y, z2, x2, y, z2, x1, y, z2, x1, y, z2, x1, y, z1);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(points, 3));
    return g;
  }, [cells]);
  useEffect(() => () => geometry.dispose(), [geometry]);

  return (
    <group>
      <lineSegments geometry={geometry}>
        <lineBasicMaterial color="#8fa6ff" transparent opacity={0.55} />
      </lineSegments>
      {highlight && (
        <mesh position={[highlight.x, SLAB + 1.4, highlight.z]}>
          <boxGeometry args={[highlight.w, 2.8, highlight.d]} />
          <meshBasicMaterial color="#7ef0ff" transparent opacity={0.8} />
        </mesh>
      )}
      {cells
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

const ARROW_ROTATION: Record<Direction, number> = {
  // стрелка по умолчанию (конус, повёрнутый на бок) смотрит в -z = вверх по схеме
  up: 0,
  left: Math.PI / 2,
  down: Math.PI,
  right: -Math.PI / 2,
};

function EntranceMarker({ x, z, dir, main }: { x: number; z: number; dir: Direction; main?: boolean }) {
  const ring = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (!ring.current) return;
    const t = (clock.elapsedTime % 2) / 2;
    ring.current.scale.setScalar(1 + t * 2.5);
    (ring.current.material as THREE.MeshBasicMaterial).opacity = 0.7 * (1 - t);
  });

  const size = main ? 1.6 : 1;
  return (
    <group position={[x, 0.3, z]} rotation={[0, ARROW_ROTATION[dir], 0]}>
      {/* стрелка стоит перед входом и указывает в здание */}
      <mesh position={[0, 0, 5 * size]} rotation={[-Math.PI / 2, 0, 0]}>
        <coneGeometry args={[2 * size, 5 * size, 3]} />
        <meshBasicMaterial color={main ? "#ffd166" : "#38c6ff"} />
      </mesh>
      {main && (
        <>
          <mesh ref={ring} rotation={[-Math.PI / 2, 0, 0]}>
            <ringGeometry args={[2.2, 3, 32]} />
            <meshBasicMaterial color="#ffd166" transparent opacity={0.7} side={THREE.DoubleSide} />
          </mesh>
          <Html position={[0, 8, 0]} center zIndexRange={[10, 0]}>
            <span className="campus-main-entrance">Главный вход</span>
          </Html>
        </>
      )}
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

export default function CampusScene({
  campusId,
  target,
  focused,
  interactive = true,
  onSelectBuilding,
}: CampusSceneProps) {
  const campus: Campus = useMemo(() => {
    const byTarget = target
      ? CAMPUSES.find((c) => c.buildings.some((b) => b.id === target.building))
      : undefined;
    return (
      CAMPUSES.find((c) => c.id === (campusId ?? byTarget?.id)) ?? CAMPUSES.find((c) => c.id === DEFAULT_CAMPUS_ID)!
    );
  }, [campusId, target]);

  const wingsById = useMemo(
    () => new Map(campus.buildings.map((b) => [b.id, b.wings.map((rect) => rectToMeters(campus, rect))])),
    [campus],
  );
  const overview = useMemo(() => boundsOf([...wingsById.values()].flat()), [wingsById]);

  const targetBuilding: Building | null =
    (target && campus.buildings.find((b) => b.id === target.building)) || null;
  const isFocused = focused && targetBuilding !== null;

  const rooms = useMemo(
    () => (targetBuilding ? buildingRooms(campus, targetBuilding) : []),
    [campus, targetBuilding],
  );
  const targetRoom = target?.room ? findRoom(rooms, target.room, target.floor) : null;
  const targetFloor = targetRoom?.floor ?? (target?.floor ? Math.min(target.floor, targetBuilding?.floors ?? 1) : null);

  // этаж «открывается», когда камера уже почти долетела - так эффект читается
  const [opened, setOpened] = useState(false);
  useEffect(() => {
    setOpened(false);
    if (!isFocused) return;
    const timer = setTimeout(() => setOpened(true), 1000);
    return () => clearTimeout(timer);
  }, [isFocused, targetBuilding, targetFloor]);

  const focus = useMemo(() => {
    if (!isFocused || !targetBuilding) return null;
    const b = boundsOf(wingsById.get(targetBuilding.id)!);
    const y = targetFloor ? (targetFloor - 1) * FLOOR_HEIGHT + SLAB : (targetBuilding.floors * FLOOR_HEIGHT) / 2;
    return { ...b, y };
  }, [isFocused, targetBuilding, targetFloor, wingsById]);

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
        const buildingPlaces = isTarget && opened ? campus.places.filter((p) => p.building === building.id) : [];

        return (
          <group key={building.id}>
            {Array.from({ length: building.floors }, (_, index) => {
              const floor = index + 1;
              let mode: FloorMode = "normal";
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
              const floorCells = isTarget && opened && floor === targetFloor ? rooms.filter((c) => c.floor === floor) : [];
              const floorPlaces = buildingPlaces.filter((p) => p.floor === floor && (targetFloor === null || floor <= targetFloor));

              return (
                <Floor
                  key={index}
                  wings={wings}
                  index={index}
                  mode={mode}
                  lift={lift}
                  onClick={interactive && onSelectBuilding ? () => onSelectBuilding(building.id) : undefined}
                >
                  {floorCells.length > 0 && <RoomsLayer cells={floorCells} highlight={targetRoom} />}
                  {floorPlaces.map((place) => {
                    const [x, z] = toMeters(campus, place.at);
                    return (
                      <Html key={place.label + place.floor} position={[x, SLAB + 2, z]} center zIndexRange={[10, 0]}>
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
        .filter((entrance) => !isFocused || entrance.main || entrance.building === targetBuilding?.id)
        .map((entrance, i) => {
          const [x, z] = toMeters(campus, entrance.at);
          return <EntranceMarker key={i} x={x} z={z} dir={entrance.dir} main={entrance.main} />;
        })}

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
