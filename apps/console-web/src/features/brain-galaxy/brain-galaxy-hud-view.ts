import type {
  BrainGraphNode,
  BrainGraphSnapshot,
  BrainNodeKind,
} from '../../lib/operator-brain-graph-view';

export type GalaxyLegendItem = {
  kind: BrainNodeKind | string;
  label: string;
  color: string;
};

export type GalaxyHubItem = {
  node_id: string;
  label: string;
  tone: string;
  detail: string;
  workspace_id: string | null;
  score: number;
};

export type GalaxyStatusChip = {
  label: string;
  value: string;
  tone: string;
};

const LEGEND: GalaxyLegendItem[] = [
  { kind: 'core', label: 'KAIRO core', color: '#48c4ff' },
  { kind: 'workspace', label: 'Workspaces', color: '#3a9fd4' },
  { kind: 'run', label: 'Active runs', color: '#6b8fa8' },
  { kind: 'signal', label: 'Signals', color: '#ffa040' },
  { kind: 'connector', label: 'Connectors', color: '#5a8cff' },
];

export function galaxyLegendItems(): GalaxyLegendItem[] {
  return LEGEND;
}

/**
 * Workspaces ranked for the left-rail "top hubs" list — attention first,
 * then critical tone, then label.
 */
export function galaxyTopHubs(snapshot: BrainGraphSnapshot | null): GalaxyHubItem[] {
  if (!snapshot) {
    return [];
  }

  const toneScore: Record<string, number> = {
    critical: 3,
    attention: 2,
    nominal: 1,
  };

  return snapshot.nodes
    .filter((node) => node.kind === 'workspace')
    .map((node) => ({
      node_id: node.node_id,
      label: node.label,
      tone: node.tone,
      detail: node.detail,
      workspace_id: node.workspace_id,
      score: toneScore[node.tone] ?? 0,
    }))
    .sort((left, right) => right.score - left.score || left.label.localeCompare(right.label));
}

export function galaxyNodeCounts(snapshot: BrainGraphSnapshot | null): Record<string, number> {
  const counts: Record<string, number> = {};
  if (!snapshot) {
    return counts;
  }
  for (const node of snapshot.nodes) {
    counts[node.kind] = (counts[node.kind] ?? 0) + 1;
  }
  return counts;
}

export function galaxyInspectorCopy(node: BrainGraphNode | null): {
  title: string;
  body: string;
  hint: string;
} {
  if (!node) {
    return {
      title: 'Inspector',
      body: 'Click a node to open its evidence panel. Workspaces focus context; signals show prove-source.',
      hint: 'Drag to orbit the galaxy',
    };
  }

  const hints: Record<string, string> = {
    core: 'KAIRO control plane — the center of your operator brain.',
    workspace: 'Evidence lists signals and runs; open the workspace in the IDE from the panel.',
    run: 'Active execution lane tied to a workspace.',
    signal: 'Evidence panel loads prove-source facts; open Attention or Continue in IDE from actions.',
    connector: 'Live connector health bound to a workspace.',
  };

  return {
    title: node.label,
    body: node.detail,
    hint: hints[node.kind] ?? 'Node in the operator brain graph.',
  };
}

export function galaxyStatusChips(
  items: Array<{ label: string; value: string; tone: string }>,
): GalaxyStatusChip[] {
  return items.slice(0, 5);
}

export function galaxyOmnibarHint(options: {
  hasActiveRun: boolean;
  runSummary: string | null;
  pendingApprovals: number;
}): string {
  if (options.pendingApprovals > 0) {
    return `${options.pendingApprovals} approval(s) waiting — open Attention or use the orbit controls below.`;
  }
  if (options.hasActiveRun && options.runSummary) {
    return `Active: ${options.runSummary.slice(0, 72)}${options.runSummary.length > 72 ? '…' : ''}`;
  }
  return "Tell KAIRO what to focus on — or click a workspace to open it.";
}

/** Workspace hub/node click: switch console context and enter the IDE. */
export function resolveGalaxyWorkspaceNavigation(workspaceId: string | null | undefined): {
  workspaceId: string;
} | null {
  const id = workspaceId?.trim() ?? '';
  if (!id) {
    return null;
  }
  return { workspaceId: id };
}
