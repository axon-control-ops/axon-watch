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
  workspace: 0.3,
  connector: 0.15,
  signal: 0.17,
  mailbox: 0.18,
  run: 0.13,
};

/** Inner workspace shell radius. */
const INNER_RADIUS = 1.55;
/** Active-run shell just outside workspaces. */
const RUN_RADIUS = 2.25;
/** Satellites (signals / connectors / mailboxes). */
const OUTER_RADIUS = 2.85;

/**
 * Place a node on a sphere shell with latitude + longitude so the galaxy
 * reads as volumetric 3D — not a flat radar ring.
 */
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
    const azimuth = (index / count) * Math.PI * 2 - Math.PI / 2;
    // Stagger latitudes so the inner ring becomes a true spherical shell.
    const band = ((index % 5) - 2) / 2;
    const elevation = band * 0.55 + Math.sin(azimuth * 2.1) * 0.18;
    workspaceAngle.set(node.workspace_id ?? node.node_id, azimuth);
    const pos = placeOnShell(INNER_RADIUS, azimuth, elevation);
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
      const spread = (index - (runNodes.length - 1) / 2) * 0.28;
      const azimuth = baseAngle + spread;
      const elevation = 0.35 + Math.cos(azimuth * 2.4) * 0.4 + index * 0.08;
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
      node.kind === 'signal' ? -0.55 : node.kind === 'mailbox' ? 0.65 : 0.15;
    const elevation = kindLift + Math.sin(azimuth * 1.7 + index) * 0.45;
    const pos = placeOnShell(OUTER_RADIUS, azimuth, elevation);
    place(node, pos.x, pos.y, pos.z);
  });

  snapshot.nodes.forEach((node, index) => {
    if (!positioned.has(node.node_id)) {
      const azimuth = (index / snapshot.nodes.length) * Math.PI * 2;
      const elevation = Math.sin(index * 1.7) * 0.5;
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
