import {
  AdditiveBlending,
  BufferGeometry,
  Color,
  Line,
  LineBasicMaterial,
  Mesh,
  MeshBasicMaterial,
  SphereGeometry,
  Vector3,
} from 'three';

import { galaxyEdgeColor } from './brain-galaxy-colors';
import type { PositionedBrainEdge3D } from './layout-brain-graph-3d';

type LiveEdgeData = {
  liveEdge: true;
  baseOpacity: number;
  phase: number;
  sourceId: string;
  targetId: string;
  focusStrength: number;
  edgeKind: string;
  sourcePos: Vector3;
  targetPos: Vector3;
  flowBead: Mesh | null;
};

const FLOW_EDGE_KINDS = new Set(['executes', 'emits']);

export function buildLiveEdge(edge: PositionedBrainEdge3D, index: number): Line {
  const sourcePos = new Vector3(edge.sourcePos.x, edge.sourcePos.y, edge.sourcePos.z);
  const targetPos = new Vector3(edge.targetPos.x, edge.targetPos.y, edge.targetPos.z);
  const geometry = new BufferGeometry().setFromPoints([sourcePos, targetPos]);
  const baseOpacity = edge.kind === 'emits' ? 0.72 : edge.kind === 'executes' ? 0.58 : 0.42;
  const material = new LineBasicMaterial({
    color: galaxyEdgeColor(edge.kind),
    transparent: true,
    opacity: baseOpacity,
    depthWrite: false,
    blending: AdditiveBlending,
  });
  const line = new Line(geometry, material);

  let flowBead: Mesh | null = null;
  if (FLOW_EDGE_KINDS.has(edge.kind)) {
    flowBead = new Mesh(
      new SphereGeometry(0.045, 10, 10),
      new MeshBasicMaterial({
        color: new Color(galaxyEdgeColor(edge.kind)),
        transparent: true,
        opacity: 0,
        depthWrite: false,
        blending: AdditiveBlending,
      }),
    );
    flowBead.position.copy(sourcePos);
    line.add(flowBead);
  }

  (line.userData as LiveEdgeData) = {
    liveEdge: true,
    baseOpacity,
    phase: index * 0.67,
    sourceId: edge.source,
    targetId: edge.target,
    focusStrength: 1,
    edgeKind: edge.kind,
    sourcePos,
    targetPos,
    flowBead,
  };
  return line;
}

export function setLiveEdgeFocus(line: Line, selectedWorkspaceId: string | null): void {
  const data = line.userData as Partial<LiveEdgeData>;
  if (!data.liveEdge) {
    return;
  }
  data.focusStrength =
    !selectedWorkspaceId ||
    data.sourceId === selectedWorkspaceId ||
    data.targetId === selectedWorkspaceId
      ? 1
      : 0.12;
}

/**
 * @param presenceAmp 0 idle · ~0.45 listening/alerting · 1 busy/speaking/autonomous
 */
export function animateLiveEdge(line: Line, clock: number, presenceAmp: number): void {
  const data = line.userData as Partial<LiveEdgeData>;
  if (!data.liveEdge) {
    return;
  }
  const amp = Math.max(0, Math.min(1, presenceAmp));
  const pulse =
    0.72 + Math.sin(clock * (1.4 + amp * 3.8) + (data.phase ?? 0)) * 0.28;
  const material = line.material as LineBasicMaterial;
  material.opacity = Math.min(
    1,
    (data.baseOpacity ?? 0.4) * pulse * (1 + amp * 0.55) * (data.focusStrength ?? 1),
  );

  const bead = data.flowBead;
  if (!bead || !data.sourcePos || !data.targetPos) {
    return;
  }
  const beadMaterial = bead.material as MeshBasicMaterial;
  // Keep packet flow alive even in quiet ambient modes.
  const flowActive = amp >= 0.2 && (data.focusStrength ?? 1) > 0.15;
  if (!flowActive) {
    beadMaterial.opacity = 0;
    return;
  }
  const speed = data.edgeKind === 'executes' ? 0.55 : 0.32;
  const t = (clock * speed + (data.phase ?? 0)) % 1;
  bead.position.lerpVectors(data.sourcePos, data.targetPos, t);
  beadMaterial.opacity = Math.min(1, 0.28 + amp * 0.7) * (data.focusStrength ?? 1);
  bead.scale.setScalar(0.85 + amp * 0.45);
}
