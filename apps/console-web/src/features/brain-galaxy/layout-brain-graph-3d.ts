import type {
  BrainGraphEdge,
  BrainGraphNode,
  BrainGraphSnapshot,
} from '../../lib/operator-brain-graph-view';
import { VAXON_CORE_ORB_RADIUS } from './vaxon-core-orb-3d';

export type PositionedBrainNode3D = BrainGraphNode & {
  x: number;
  y: number;
  z: number;
  radius: number;
};

export type PositionedBrainEdge3D = BrainGraphEdge & {
  sourcePos: { x: number; y: number; z: number };
  targetPos: { x: number; y: number; z: number };
};

export type BrainGraphLayout3D = {
  nodes: PositionedBrainNode3D[];
  edges: PositionedBrainEdge3D[];
};

const NODE_RADIUS: Record<string, number> = {
  core: VAXON_CORE_ORB_RADIUS,
  workspace: 0.24,
  connector: 0.2,
  signal: 0.22,
  mailbox: 0.15,
  run: 0.11,
};

/**
 * Dense-but-readable shells: tight enough for the nebula look, wide enough
 * that ~17 workspaces don't collapse onto the core.
 */
const INNER_RADIUS = 2.35;
const RUN_RADIUS = 3.25;
const OUTER_RADIUS = 4.05;

function placeOnShell(
  radius: number,
  azimuth: number,
  elevation: number,
): { x: number; y: number; z: number } {
  const cosEl = Math.cos(elevation);
  return {
    x: Math.cos(azimuth) * cosEl * radius,
    y: Math.sin(elevation) * radius,
    z: Math.sin(azimuth) * cosEl * radius,
  };
}

/**
 * Deterministic 3D radial layout — same DTO in, same positions out.
 * Workspaces sit on an inner sphere shell; runs fan outward; satellites
 * orbit on an outer shell with real vertical depth.
 */
export function layoutBrainGraph3D(snapshot: BrainGraphSnapshot | null): BrainGraphLayout3D {
  if (!snapshot || snapshot.nodes.length === 0) {
    return { nodes: [], edges: [] };
  }

  const positioned = new Map<string, PositionedBrainNode3D>();

  const place = (node: BrainGraphNode, x: number, y: number, z: number): void => {
    positioned.set(node.node_id, {
      ...node,
      x,
      y,
      z,
      radius: NODE_RADIUS[node.kind] ?? 0.14,
    });
  };

  const core = snapshot.nodes.find((node) => node.kind === 'core');
  if (core) {
    place(core, 0, 0, 0);
  }

  const workspaces = snapshot.nodes.filter((node) => node.kind === 'workspace');
  const workspaceAngle = new Map<string, number>();
  workspaces.forEach((node, index) => {
    const count = Math.max(workspaces.length, 1);
    // Slight golden-angle jitter so equal counts don't form a perfect radar disc.
    const azimuth = (index / count) * Math.PI * 2 - Math.PI / 2 + (index % 3) * 0.04;
    const band = ((index % 5) - 2) / 2;
    const elevation = band * 0.62 + Math.sin(azimuth * 2.1) * 0.22;
    workspaceAngle.set(node.workspace_id ?? node.node_id, azimuth);
    // Alternate shell depth so neighbors don't stack in screen space.
    const radius = INNER_RADIUS + (index % 2) * 0.28;
    const pos = placeOnShell(radius, azimuth, elevation);
    place(node, pos.x, pos.y, pos.z);
  });

  const runsByWorkspace = new Map<string, BrainGraphNode[]>();
  for (const node of snapshot.nodes) {
    if (node.kind !== 'run') {
      continue;
    }
    const key = node.workspace_id ?? '';
    const bucket = runsByWorkspace.get(key) ?? [];
    bucket.push(node);
    runsByWorkspace.set(key, bucket);
  }
  for (const [workspaceId, runNodes] of runsByWorkspace) {
    const baseAngle = workspaceAngle.get(workspaceId) ?? -Math.PI / 2;
    runNodes.forEach((node, index) => {
      const spread = (index - (runNodes.length - 1) / 2) * 0.32;
      const azimuth = baseAngle + spread;
      const elevation = 0.4 + Math.cos(azimuth * 2.4) * 0.35 + index * 0.1;
      const pos = placeOnShell(RUN_RADIUS, azimuth, elevation);
      place(node, pos.x, pos.y, pos.z);
    });
  }

  const satellites = snapshot.nodes.filter(
    (node) => node.kind === 'signal' || node.kind === 'connector' || node.kind === 'mailbox',
  );
  satellites.forEach((node, index) => {
    const boundAngle = node.workspace_id ? workspaceAngle.get(node.workspace_id) : undefined;
    const kindOffset =
      node.kind === 'signal' ? 0.55 : node.kind === 'mailbox' ? 0.9 : -0.45;
    const azimuth =
      boundAngle !== undefined
        ? boundAngle + kindOffset
        : (index / Math.max(satellites.length, 1)) * Math.PI * 2 + Math.PI / 4;
    const kindLift =
      node.kind === 'signal' ? -0.7 : node.kind === 'mailbox' ? 0.75 : 0.2;
    const elevation = kindLift + Math.sin(azimuth * 1.7 + index) * 0.4;
    const pos = placeOnShell(OUTER_RADIUS, azimuth, elevation);
    place(node, pos.x, pos.y, pos.z);
  });

  snapshot.nodes.forEach((node, index) => {
    if (!positioned.has(node.node_id)) {
      const azimuth = (index / snapshot.nodes.length) * Math.PI * 2;
      const elevation = Math.sin(index * 1.7) * 0.55;
      const pos = placeOnShell(OUTER_RADIUS, azimuth, elevation);
      place(node, pos.x, pos.y, pos.z);
    }
  });

  const edges: PositionedBrainEdge3D[] = [];
  for (const edge of snapshot.edges) {
    const source = positioned.get(edge.source);
    const target = positioned.get(edge.target);
    if (!source || !target) {
      continue;
    }
    edges.push({
      ...edge,
      sourcePos: { x: source.x, y: source.y, z: source.z },
      targetPos: { x: target.x, y: target.y, z: target.z },
    });
  }

  return { nodes: [...positioned.values()], edges };
}
