import type {
  BrainGraphEdge,
  BrainGraphNode,
  BrainGraphSnapshot,
} from '../../lib/operator-brain-graph-view';

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
  core: 0.42,
  workspace: 0.28,
  connector: 0.14,
  signal: 0.16,
  run: 0.12,
};

const INNER_RADIUS = 1.35;
const RUN_RADIUS = 2.05;
const OUTER_RADIUS = 2.55;

/**
 * Deterministic 3D radial layout — same DTO in, same positions out.
 * Workspaces sit on an inner sphere shell; runs fan outward; satellites
 * orbit on an outer shell with slight depth variation per workspace.
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
    const angle = (index / Math.max(workspaces.length, 1)) * Math.PI * 2 - Math.PI / 2;
    workspaceAngle.set(node.workspace_id ?? node.node_id, angle);
    const tilt = Math.sin(angle * 2) * 0.35;
    place(
      node,
      Math.cos(angle) * INNER_RADIUS,
      tilt,
      Math.sin(angle) * INNER_RADIUS,
    );
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
      const angle = baseAngle + spread;
      const lift = Math.cos(angle * 3) * 0.2;
      place(
        node,
        Math.cos(angle) * RUN_RADIUS,
        lift,
        Math.sin(angle) * RUN_RADIUS,
      );
    });
  }

  const satellites = snapshot.nodes.filter(
    (node) => node.kind === 'signal' || node.kind === 'connector',
  );
  satellites.forEach((node, index) => {
    const boundAngle = node.workspace_id ? workspaceAngle.get(node.workspace_id) : undefined;
    const angle =
      boundAngle !== undefined
        ? boundAngle + (node.kind === 'signal' ? 0.55 : -0.45)
        : (index / Math.max(satellites.length, 1)) * Math.PI * 2 + Math.PI / 4;
    const depth = Math.sin(angle * 1.5) * 0.45;
    place(
      node,
      Math.cos(angle) * OUTER_RADIUS,
      depth,
      Math.sin(angle) * OUTER_RADIUS,
    );
  });

  snapshot.nodes.forEach((node, index) => {
    if (!positioned.has(node.node_id)) {
      const angle = (index / snapshot.nodes.length) * Math.PI * 2;
      place(
        node,
        Math.cos(angle) * OUTER_RADIUS,
        0,
        Math.sin(angle) * OUTER_RADIUS,
      );
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
