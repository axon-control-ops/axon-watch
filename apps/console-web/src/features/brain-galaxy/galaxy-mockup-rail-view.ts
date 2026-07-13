import { canonicalWorkspaceLabel } from '../../lib/kairo-entity-labels';
import type { BrainGraphSnapshot } from '../../lib/operator-brain-graph-view';
import type { WorkspaceRecord } from '../../contracts/canonical';

export type GalaxyMockupRailItem = {
  id: string;
  label: string;
  detail: string;
  kind: 'core' | 'workspace';
  workspace_id: string | null;
  tone: string;
  icon: 'core' | 'shield' | 'pulse' | 'folder' | 'signal';
};

function workspaceIcon(index: number): GalaxyMockupRailItem['icon'] {
  const icons: GalaxyMockupRailItem['icon'][] = ['shield', 'pulse', 'folder', 'signal'];
  return icons[index % icons.length] ?? 'folder';
}

function workspaceChildStats(
  snapshot: BrainGraphSnapshot | null,
  workspaceId: string,
): { nodes: number; links: number } {
  if (!snapshot) {
    return { nodes: 0, links: 0 };
  }
  const nodeIds = new Set(
    snapshot.nodes
      .filter((node) => node.workspace_id === workspaceId || node.node_id === `ws_${workspaceId}`)
      .map((node) => node.node_id),
  );
  const links = snapshot.edges.filter(
    (edge) => nodeIds.has(edge.source) || nodeIds.has(edge.target),
  ).length;
  return { nodes: Math.max(nodeIds.size, 1), links };
}

/** Mockup-style left rail: VAXON Core first, then workspaces with node/link counts. */
export function galaxyMockupRailItems(
  snapshot: BrainGraphSnapshot | null,
  workspaces: WorkspaceRecord[],
): GalaxyMockupRailItem[] {
  const items: GalaxyMockupRailItem[] = [];
  const core = snapshot?.nodes.find((node) => node.kind === 'core') ?? null;
  if (core) {
    items.push({
      id: core.node_id,
      label: core.label || 'VAXON Core',
      detail: `${snapshot?.node_count ?? 0} nodes · ${snapshot?.edge_count ?? 0} links`,
      kind: 'core',
      workspace_id: null,
      tone: core.tone || 'nominal',
      icon: 'core',
    });
  }

  workspaces.forEach((workspace, index) => {
    const workspaceId = workspace.workspace_id;
    const stats = workspaceChildStats(snapshot, workspaceId);
    const graphNode =
      snapshot?.nodes.find(
        (node) => node.kind === 'workspace' && node.workspace_id === workspaceId,
      ) ?? null;
    items.push({
      id: graphNode?.node_id ?? `ws_${workspaceId}`,
      label: canonicalWorkspaceLabel(workspaceId, workspace.display_name),
      detail: `${stats.nodes} nodes · ${stats.links} links`,
      kind: 'workspace',
      workspace_id: workspaceId,
      tone: graphNode?.tone || 'nominal',
      icon: workspaceIcon(index),
    });
  });

  return items;
}
