import type {
  BrainGraphLayout,
  BrainGraphSnapshot,
  PositionedBrainNode,
} from '../../lib/operator-brain-graph-view';
import { layoutBrainGraph3D } from './layout-brain-graph-3d';

/** Side-biased camera so the SVG fallback reads as a cloud, not a top-down disc. */
const SVG_CAMERA = { x: 3.4, y: 1.35, z: 4.6 } as const;

export type ProjectedBrainNode = PositionedBrainNode & {
  depthScale: number;
  showLabel: boolean;
};

export type ProjectedBrainGraphLayout = Omit<BrainGraphLayout, 'nodes'> & {
  nodes: ProjectedBrainNode[];
  nebula: { cx: number; cy: number; rx: number; ry: number };
  stars: Array<{ x: number; y: number; r: number; o: number }>;
};

const NODE_RADIUS_2D: Record<string, number> = {
  core: 26,
  workspace: 11,
  connector: 14,
  signal: 16,
  mailbox: 10,
  run: 7,
};

function seeded(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 0x100000000;
  };
}

/**
 * Project the 3D nebula cluster into SVG — used when WebGL is unavailable
 * so the operator still sees labeled glowing cloud, not a flat radar ring.
 */
export function projectBrainGraph3DToSvg(
  snapshot: BrainGraphSnapshot | null,
  options?: { width?: number; height?: number },
): ProjectedBrainGraphLayout {
  const width = options?.width ?? 640;
  const height = options?.height ?? 400;
  const layout3d = layoutBrainGraph3D(snapshot);
  if (layout3d.nodes.length === 0) {
    return {
      width,
      height,
      nodes: [],
      edges: [],
      nebula: { cx: width / 2, cy: height / 2, rx: 80, ry: 50 },
      stars: [],
    };
  }

  const cam = SVG_CAMERA;
  const camLen = Math.hypot(cam.x, cam.y, cam.z) || 1;
  const forward = { x: -cam.x / camLen, y: -cam.y / camLen, z: -cam.z / camLen };
  const worldUp = { x: 0, y: 1, z: 0 };
  let right = {
    x: forward.y * worldUp.z - forward.z * worldUp.y,
    y: forward.z * worldUp.x - forward.x * worldUp.z,
    z: forward.x * worldUp.y - forward.y * worldUp.x,
  };
  const rightLen = Math.hypot(right.x, right.y, right.z) || 1;
  right = { x: right.x / rightLen, y: right.y / rightLen, z: right.z / rightLen };
  const up = {
    x: right.y * forward.z - right.z * forward.y,
    y: right.z * forward.x - right.x * forward.z,
    z: right.x * forward.y - right.y * forward.x,
  };

  const focal = Math.min(width, height) * 1.15;
  const cx = width / 2;
  const cy = height / 2 + height * 0.04;

  const project = (x: number, y: number, z: number): { x: number; y: number; scale: number } => {
    const vx = x - cam.x;
    const vy = y - cam.y;
    const vz = z - cam.z;
    const depth = vx * forward.x + vy * forward.y + vz * forward.z;
    const safeDepth = Math.max(depth, 0.7);
    const rx = vx * right.x + vy * right.y + vz * right.z;
    const ry = vx * up.x + vy * up.y + vz * up.z;
    const scale = focal / safeDepth;
    return {
      x: cx + rx * scale,
      y: cy - ry * scale,
      scale: Math.max(0.55, Math.min(1.6, scale / (focal / camLen))),
    };
  };

  const projected = new Map<string, { x: number; y: number; scale: number }>();
  for (const node of layout3d.nodes) {
    projected.set(node.node_id, project(node.x, node.y, node.z));
  }

  const nodes: ProjectedBrainNode[] = layout3d.nodes
    .map((node) => {
      const p = projected.get(node.node_id)!;
      const base = NODE_RADIUS_2D[node.kind] ?? 9;
      const showLabel =
        node.kind === 'core' ||
        node.kind === 'workspace' ||
        node.kind === 'signal' ||
        node.kind === 'connector';
      return {
        ...node,
        x: p.x,
        y: p.y,
        radius: base * p.scale,
        depthScale: p.scale,
        showLabel,
      };
    })
    .sort((a, b) => a.depthScale - b.depthScale);

  const edges = layout3d.edges.map((edge) => {
    const source = projected.get(edge.source)!;
    const target = projected.get(edge.target)!;
    return {
      ...edge,
      x1: source.x,
      y1: source.y,
      x2: target.x,
      y2: target.y,
    };
  });

  const labeled = nodes.filter((n) => n.showLabel);
  const xs = labeled.map((n) => n.x);
  const ys = labeled.map((n) => n.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const rand = seeded(26);
  const stars = Array.from({ length: 90 }, () => ({
    x: rand() * width,
    y: rand() * height,
    r: 0.6 + rand() * 1.4,
    o: 0.15 + rand() * 0.55,
  }));

  return {
    width,
    height,
    nodes,
    edges,
    nebula: {
      cx: (minX + maxX) / 2,
      cy: (minY + maxY) / 2,
      rx: Math.max(70, (maxX - minX) * 0.72 + 36),
      ry: Math.max(48, (maxY - minY) * 0.78 + 28),
    },
    stars,
  };
}
