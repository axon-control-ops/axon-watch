export type BrainNodeKind = 'core' | 'workspace' | 'run' | 'signal' | 'connector' | 'mailbox';
export type BrainNodeTone = 'nominal' | 'attention' | 'critical';

export type BrainGraphNode = {
  node_id: string;
  kind: BrainNodeKind | string;
  label: string;
  tone: BrainNodeTone | string;
  workspace_id: string | null;
  detail: string;
};

export type BrainGraphEdge = {
  edge_id: string;
  source: string;
  target: string;
  kind: string;
};

export type BrainGraphSnapshot = {
  generated_at: string;
  watch_connected: boolean;
  nodes: BrainGraphNode[];
  edges: BrainGraphEdge[];
  node_count: number;
  edge_count: number;
};

export type PositionedBrainNode = BrainGraphNode & {
  x: number;
  y: number;
  radius: number;
};

export type PositionedBrainEdge = BrainGraphEdge & {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
};

export type BrainGraphLayout = {
  width: number;
  height: number;
  nodes: PositionedBrainNode[];
  edges: PositionedBrainEdge[];
};

const NODE_RADIUS: Record<string, number> = {
  core: 26,
  workspace: 18,
  connector: 10,
  signal: 11,
  mailbox: 12,
  run: 9,
};

/**
 * Deterministic radial layout: KAIRO core at center, workspaces on an inner
 * ring, their runs fanned just outside each workspace, and signals/connectors
 * on an outer ring near their workspace (or evenly spread when unbound).
 * No physics — same DTO in, same picture out.
 */
export function layoutBrainGraph(
  snapshot: BrainGraphSnapshot | null,
  options?: { width?: number; height?: number },
): BrainGraphLayout {
  const width = options?.width ?? 640;
  const height = options?.height ?? 420;

  if (!snapshot || snapshot.nodes.length === 0) {
    return { width, height, nodes: [], edges: [] };
  }

  const cx = width / 2;
  const cy = height / 2;
  const innerRadius = Math.min(width, height) * 0.26;
  const runRadius = Math.min(width, height) * 0.4;
  const outerRadius = Math.min(width, height) * 0.46;

  const positioned = new Map<string, PositionedBrainNode>();

  const place = (node: BrainGraphNode, x: number, y: number): void => {
    positioned.set(node.node_id, {
      ...node,
      x,
      y,
      radius: NODE_RADIUS[node.kind] ?? 10,
    });
  };

  const core = snapshot.nodes.find((node) => node.kind === 'core');
  if (core) {
    place(core, cx, cy);
  }

  const workspaces = snapshot.nodes.filter((node) => node.kind === 'workspace');
  const workspaceAngle = new Map<string, number>();
  workspaces.forEach((node, index) => {
    const angle = (index / Math.max(workspaces.length, 1)) * Math.PI * 2 - Math.PI / 2;
    workspaceAngle.set(node.workspace_id ?? node.node_id, angle);
    place(node, cx + Math.cos(angle) * innerRadius, cy + Math.sin(angle) * innerRadius);
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
      const angle = baseAngle + spread;
      place(node, cx + Math.cos(angle) * runRadius, cy + Math.sin(angle) * runRadius);
    });
  }

  const satellites = snapshot.nodes.filter(
    (node) => node.kind === 'signal' || node.kind === 'connector' || node.kind === 'mailbox',
  );
  satellites.forEach((node, index) => {
    const boundAngle = node.workspace_id ? workspaceAngle.get(node.workspace_id) : undefined;
    const kindOffset =
      node.kind === 'signal' ? 0.5 : node.kind === 'mailbox' ? 0.85 : -0.5;
    const angle =
      boundAngle !== undefined
        ? boundAngle + kindOffset
        : (index / Math.max(satellites.length, 1)) * Math.PI * 2 + Math.PI / 4;
    place(node, cx + Math.cos(angle) * outerRadius, cy + Math.sin(angle) * outerRadius);
  });

  // Any node the passes above missed (unknown kind) still gets a spot.
  snapshot.nodes.forEach((node, index) => {
    if (!positioned.has(node.node_id)) {
      const angle = (index / snapshot.nodes.length) * Math.PI * 2;
      place(node, cx + Math.cos(angle) * outerRadius, cy + Math.sin(angle) * outerRadius);
    }
  });

  const edges: PositionedBrainEdge[] = [];
  for (const edge of snapshot.edges) {
    const source = positioned.get(edge.source);
    const target = positioned.get(edge.target);
    if (!source || !target) {
      continue;
    }
    edges.push({ ...edge, x1: source.x, y1: source.y, x2: target.x, y2: target.y });
  }

  return {
    width,
    height,
    nodes: [...positioned.values()],
    edges,
  };
}

export function brainGraphHeadline(snapshot: BrainGraphSnapshot | null): string {
  if (!snapshot) {
    return 'Loading brain graph…';
  }
  if (!snapshot.watch_connected) {
    return 'Watch disconnected — partial graph';
  }
  const attention = snapshot.nodes.filter((node) => node.tone !== 'nominal').length;
  if (attention === 0) {
    return `${snapshot.node_count} nodes · all nominal`;
  }
  return `${snapshot.node_count} nodes · ${attention} need attention`;
}

export type OperatorCenterView = 'grid' | 'graph';

const CENTER_VIEW_STORAGE_KEY = 'axon.operator.center-view';

export function readStoredOperatorCenterView(): OperatorCenterView {
  if (typeof sessionStorage === 'undefined') {
    return 'graph';
  }
  const stored = sessionStorage.getItem(CENTER_VIEW_STORAGE_KEY);
  return stored === 'grid' ? 'grid' : 'graph';
}

export function persistOperatorCenterView(view: OperatorCenterView): void {
  if (typeof sessionStorage === 'undefined') {
    return;
  }
  sessionStorage.setItem(CENTER_VIEW_STORAGE_KEY, view);
}
