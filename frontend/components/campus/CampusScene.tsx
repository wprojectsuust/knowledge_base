"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { CameraControls, Edges, Grid, Html } from "@react-three/drei";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import * as THREE from "three";
import { CAMPUSES, DEFAULT_CAMPUS_ID, FLOOR_HEIGHT, type Building, type Campus } from "@/lib/campus-data";

export type CampusTarget = {
  building: string;
  room?: string | null;
  floor?: number | null;
};

type CampusSceneProps = {
  campusId?: string;
  target?: CampusTarget | null;
  /** true - камера летит к цели и раскрывает этажи; false - медленный облёт всего кампуса */
  focused: boolean;
  /** можно ли крутить сцену мышью (в мини-окне в углу - нет) */
  interactive?: boolean;
  onSelectBuilding?: (id: string) => void;
};

const EXPLODE_GAP = 7; // насколько раздвигаются этажи при раскрытии корпуса
const SLAB_RATIO = 0.82; // толщина плиты этажа от высоты этажа - между плитами видны щели

const COLORS = {
  body: new THREE.Color("#2f4dff"),
  edge: "#6f8bff",
  edgeDim: "#1f2d78",
  edgeTarget: "#c9d6ff",
  room: "#7ef0ff",
};

/** Центр кампуса - чтобы сцена крутилась вокруг середины, а не вокруг произвольной точки. */
function campusCenter(campus: Campus) {
  const xs = campus.buildings.flatMap((b) => [b.x - b.w / 2, b.x + b.w / 2]);
  const zs = campus.buildings.flatMap((b) => [b.z - b.d / 2, b.z + b.d / 2]);
  return new THREE.Vector3((Math.min(...xs) + Math.max(...xs)) / 2, 0, (Math.min(...zs) + Math.max(...zs)) / 2);
}

function floorBaseY(floorIndex: number, exploded: boolean) {
  return floorIndex * FLOOR_HEIGHT + (exploded ? floorIndex * EXPLODE_GAP : 0);
}

type FloorProps = {
  building: Building;
  index: number;
  exploded: boolean;
  opacity: number;
  edgeColor: string;
  slideOut: boolean;
  onClick?: () => void;
};

function FloorSlab({ building, index, exploded, opacity, edgeColor, slideOut, onClick }: FloorProps) {
  const group = useRef<THREE.Group>(null);
  const material = useRef<THREE.MeshStandardMaterial>(null);
  const slabHeight = FLOOR_HEIGHT * SLAB_RATIO;

  useFrame((_, delta) => {
    if (!group.current || !material.current) return;
    const k = 1 - Math.exp(-delta * 4); // плавное приближение к цели, не зависящее от FPS
    const targetY = floorBaseY(index, exploded) + slabHeight / 2;
    const targetZ = slideOut ? building.d * 0.45 : 0;
    group.current.position.y += (targetY - group.current.position.y) * k;
    group.current.position.z += (targetZ - group.current.position.z) * k;
    material.current.opacity += (opacity - material.current.opacity) * k;
  });

  return (
    <group ref={group} position={[0, floorBaseY(index, false) + slabHeight / 2, 0]}>
      <mesh
        onClick={(event) => {
          if (!onClick) return;
          event.stopPropagation();
          onClick();
        }}
      >
        <boxGeometry args={[building.w, slabHeight, building.d]} />
        <meshStandardMaterial
          ref={material}
          color={COLORS.body}
          emissive={COLORS.body}
          emissiveIntensity={0.35}
          transparent
          opacity={opacity}
          depthWrite={false}
        />
        <Edges color={edgeColor} lineWidth={1} />
      </mesh>
    </group>
  );
}

type BuildingProps = {
  building: Building;
  state: "normal" | "dimmed" | "target";
  exploded: boolean;
  targetFloor: number | null;
  targetRoom: string | null;
  onSelect?: (id: string) => void;
};

function BuildingModel({ building, state, exploded, targetFloor, targetRoom, onSelect }: BuildingProps) {
  const isTarget = state === "target";
  const floorIndex = targetFloor ? Math.min(targetFloor, building.floors) - 1 : null;
  const room = building.rooms?.find((item) => item.number === targetRoom) ?? null;
  const topY = floorBaseY(building.floors, false);

  // куда ставить пин: в кабинет, если он размечен, иначе в центр нужного этажа (или над корпусом)
  const pinFloorIndex = room ? room.floor - 1 : floorIndex;
  const pinY = pinFloorIndex !== null ? floorBaseY(pinFloorIndex, exploded) + FLOOR_HEIGHT : topY + 2;
  const pinX = room ? (room.u - 0.5) * building.w : 0;
  const pinZ = (room ? (room.v - 0.5) * building.d : 0) + (isTarget && exploded && pinFloorIndex !== null ? building.d * 0.45 : 0);

  return (
    <group position={[building.x, 0, building.z]} rotation={[0, THREE.MathUtils.degToRad(building.rotation ?? 0), 0]}>
      {Array.from({ length: building.floors }, (_, index) => {
        const isTargetFloor = isTarget && floorIndex === index;
        let opacity = 0.32;
        let edgeColor = COLORS.edge;
        if (state === "dimmed") {
          opacity = 0.06;
          edgeColor = COLORS.edgeDim;
        } else if (isTarget && floorIndex !== null) {
          opacity = isTargetFloor ? 0.6 : 0.1;
          edgeColor = isTargetFloor ? COLORS.edgeTarget : COLORS.edge;
        } else if (isTarget) {
          opacity = 0.45;
          edgeColor = COLORS.edgeTarget;
        }
        return (
          <FloorSlab
            key={index}
            building={building}
            index={index}
            exploded={isTarget && exploded}
            opacity={opacity}
            edgeColor={edgeColor}
            slideOut={isTargetFloor && exploded}
            onClick={onSelect ? () => onSelect(building.id) : undefined}
          />
        );
      })}

      {isTarget && room && exploded && (
        <mesh position={[pinX, pinY - FLOOR_HEIGHT * 0.55, pinZ]}>
          <boxGeometry args={[building.w * 0.12, FLOOR_HEIGHT * 0.5, building.d * 0.3]} />
          <meshBasicMaterial color={COLORS.room} transparent opacity={0.85} />
        </mesh>
      )}

      {state !== "dimmed" && !isTarget && (
        <Html position={[0, topY + 3, 0]} center zIndexRange={[10, 0]} className="campus-label-wrap">
          <span className="campus-label">{building.id}</span>
        </Html>
      )}

      {isTarget && (
        <Html position={[pinX, pinY + 1, pinZ]} center zIndexRange={[10, 0]} className="campus-label-wrap">
          <div className={`campus-pin${exploded ? " dropped" : ""}`}>
            <span className="campus-pin-title">
              {targetRoom ? `${building.id}-${targetRoom}` : building.name}
            </span>
            {floorIndex !== null && <span className="campus-pin-sub">{floorIndex + 1} этаж</span>}
          </div>
        </Html>
      )}
    </group>
  );
}

function BridgeModel({ from, to, floor, dimmed }: { from: Building; to: Building; floor: number; dimmed: boolean }) {
  const material = useRef<THREE.MeshStandardMaterial>(null);
  const start = new THREE.Vector3(from.x, 0, from.z);
  const end = new THREE.Vector3(to.x, 0, to.z);
  const length = start.distanceTo(end);
  const middle = start.clone().add(end).multiplyScalar(0.5);
  const angle = Math.atan2(end.x - start.x, end.z - start.z);
  const y = (floor - 1) * FLOOR_HEIGHT + FLOOR_HEIGHT * 0.45;

  useFrame((_, delta) => {
    if (!material.current) return;
    const k = 1 - Math.exp(-delta * 4);
    material.current.opacity += ((dimmed ? 0.04 : 0.35) - material.current.opacity) * k;
  });

  return (
    <mesh position={[middle.x, y, middle.z]} rotation={[0, angle, 0]}>
      <boxGeometry args={[3, 2.4, length]} />
      <meshStandardMaterial
        ref={material}
        color="#38c6ff"
        emissive="#38c6ff"
        emissiveIntensity={0.6}
        transparent
        opacity={0.35}
        depthWrite={false}
      />
    </mesh>
  );
}

function CameraRig({
  controls,
  campus,
  offset,
  target,
  focused,
}: {
  controls: React.RefObject<CameraControls | null>;
  campus: Campus;
  offset: THREE.Vector3;
  target: Building | null;
  focused: boolean;
}) {
  useEffect(() => {
    const cc = controls.current;
    if (!cc) return;
    if (focused && target) {
      // встаём перед корпусом (со стороны его локальной +z, куда выезжает этаж) и чуть сверху
      const angle = THREE.MathUtils.degToRad(target.rotation ?? 0);
      const center = new THREE.Vector3(target.x, 0, target.z).sub(offset);
      const lookY = (target.floors * (FLOOR_HEIGHT + EXPLODE_GAP)) / 2;
      const distance = Math.max(target.w, target.d) * 1.25 + 60;
      const dir = new THREE.Vector3(Math.sin(angle) * 0.55, 0, Math.cos(angle)).normalize();
      const position = center.clone().addScaledVector(dir, distance).setY(lookY + distance * 0.45);
      void cc.setLookAt(position.x, position.y, position.z, center.x, lookY, center.z, true);
    } else {
      const size = Math.max(...campus.buildings.map((b) => Math.hypot(b.x - offset.x, b.z - offset.z))) + 60;
      void cc.setLookAt(size * 0.9, size * 0.85, size * 1.3, 0, 0, 0, true);
    }
  }, [controls, campus, offset, target, focused]);

  useFrame((_, delta) => {
    // медленный облёт, пока ни на что не смотрим
    if (!focused) controls.current?.rotate(delta * 0.06, 0, true);
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
  const targetInfo = useMemo(() => {
    if (!target) return null;
    for (const campus of CAMPUSES) {
      const building = campus.buildings.find((item) => item.id === target.building);
      if (building) return { campus, building };
    }
    return null;
  }, [target]);

  const campus =
    CAMPUSES.find((item) => item.id === (campusId ?? targetInfo?.campus.id)) ??
    CAMPUSES.find((item) => item.id === DEFAULT_CAMPUS_ID)!;
  const offset = useMemo(() => campusCenter(campus), [campus]);
  const targetBuilding = targetInfo && targetInfo.campus.id === campus.id ? targetInfo.building : null;
  const isFocused = focused && targetBuilding !== null;

  // этажи раздвигаются, когда камера уже почти долетела - так эффект читается
  const [exploded, setExploded] = useState(false);
  useEffect(() => {
    if (!isFocused) {
      setExploded(false);
      return;
    }
    const timer = setTimeout(() => setExploded(true), 1100);
    return () => clearTimeout(timer);
  }, [isFocused, targetBuilding]);

  const controls = useRef<CameraControls | null>(null);
  const byId = new Map(campus.buildings.map((b) => [b.id, b]));

  return (
    <Canvas camera={{ position: [260, 220, 340], fov: 38, near: 1, far: 3000 }} dpr={[1, 2]}>
      <color attach="background" args={["#050b24"]} />
      <fog attach="fog" args={["#050b24", 300, 900]} />
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
        fadeDistance={700}
        fadeStrength={1.4}
        position={[0, -0.05, 0]}
      />

      <group position={[-offset.x, 0, -offset.z]}>
        {campus.bridges.map((bridge) => {
          const from = byId.get(bridge.from);
          const to = byId.get(bridge.to);
          if (!from || !to) return null;
          return (
            <BridgeModel
              key={`${bridge.from}-${bridge.to}`}
              from={from}
              to={to}
              floor={bridge.floor}
              dimmed={isFocused}
            />
          );
        })}
        {campus.buildings.map((building) => (
          <BuildingModel
            key={building.id}
            building={building}
            state={!isFocused ? "normal" : building === targetBuilding ? "target" : "dimmed"}
            exploded={exploded && building === targetBuilding}
            targetFloor={building === targetBuilding ? target?.floor ?? null : null}
            targetRoom={building === targetBuilding ? target?.room ?? null : null}
            onSelect={interactive ? onSelectBuilding : undefined}
          />
        ))}
      </group>

      <CameraControls
        ref={controls}
        enabled={interactive}
        smoothTime={0.9}
        minDistance={40}
        maxDistance={900}
        maxPolarAngle={Math.PI * 0.45}
      />
      <CameraRig controls={controls} campus={campus} offset={offset} target={targetBuilding} focused={isFocused} />

      <EffectComposer>
        <Bloom mipmapBlur luminanceThreshold={0.15} intensity={0.9} radius={0.7} />
      </EffectComposer>
    </Canvas>
  );
}
