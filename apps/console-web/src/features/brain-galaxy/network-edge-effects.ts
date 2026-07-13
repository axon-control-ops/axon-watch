import {
  AdditiveBlending,
  BufferGeometry,
  Line,
  LineBasicMaterial,
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
};

export function buildLiveEdge(edge: PositionedBrainEdge3D, index: number): Line {
  const geometry = new BufferGeometry().setFromPoints([
    new Vector3(edge.sourcePos.x, edge.sourcePos.y, edge.sourcePos.z),
    new Vector3(edge.targetPos.x, edge.targetPos.y, edge.targetPos.z),
  ]);
  const baseOpacity = edge.kind === 'emits' ? 0.72 : edge.kind === 'executes' ? 0.58 : 0.42;
  const material = new LineBasicMaterial({
    color: galaxyEdgeColor(edge.kind),
    transparent: true,
    opacity: baseOpacity,
    depthWrite: false,
    blending: AdditiveBlending,
  });
  const line = new Line(geometry, material);
  (line.userData as LiveEdgeData) = {
    liveEdge: true,
    baseOpacity,
    phase: index * 0.67,
    sourceId: edge.source,
    targetId: edge.target,
    focusStrength: 1,
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

export function animateLiveEdge(line: Line, clock: number, busy: boolean): void {
  const data = line.userData as Partial<LiveEdgeData>;
  if (!data.liveEdge) {
    return;
  }
  const pulse = 0.72 + Math.sin(clock * (busy ? 5.2 : 1.4) + (data.phase ?? 0)) * 0.28;
  const material = line.material as LineBasicMaterial;
  material.opacity = Math.min(
    1,
    (data.baseOpacity ?? 0.4) *
      pulse *
      (busy ? 1.55 : 1) *
      (data.focusStrength ?? 1),
  );
}
