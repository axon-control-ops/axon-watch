import { describe, expect, it } from 'vitest';

import {
  galaxyInspectorCopy,
  galaxyLegendItems,
  galaxyNodeCounts,
  galaxyOmnibarHint,
  galaxyTopHubs,
  resolveGalaxyWorkspaceNavigation,
} from './brain-galaxy-hud-view';
import type { BrainGraphSnapshot } from '../../lib/operator-brain-graph-view';

const snapshot: BrainGraphSnapshot = {
  generated_at: '2026-07-07T21:00:00Z',
  watch_connected: true,
  node_count: 4,
  edge_count: 2,
  nodes: [
    {
      node_id: 'core_kairo',
      kind: 'core',
      label: 'KAIRO',
      tone: 'nominal',
      workspace_id: null,
      detail: 'Control plane',
    },
    {
      node_id: 'ws_dashpro',
      kind: 'workspace',
      label: 'DashPro',
      tone: 'critical',
      workspace_id: 'workspace_dashpro',
      detail: '2 signals',
    },
    {
      node_id: 'ws_axon',
      kind: 'workspace',
      label: 'axon-watch',
      tone: 'nominal',
      workspace_id: 'workspace_axon_watch',
      detail: 'nominal',
    },
    {
      node_id: 'sig_1',
      kind: 'signal',
      label: 'Sentry',
      tone: 'attention',
      workspace_id: 'workspace_dashpro',
      detail: 'high',
    },
  ],
  edges: [],
};

describe('brain-galaxy-hud-view', () => {
  it('returns legend entries for every node kind', () => {
    expect(galaxyLegendItems().length).toBeGreaterThanOrEqual(5);
  });

  it('ranks critical workspaces first in top hubs', () => {
    const hubs = galaxyTopHubs(snapshot);
    expect(hubs[0]?.label).toBe('DashPro');
  });

  it('counts nodes by kind', () => {
    expect(galaxyNodeCounts(snapshot).workspace).toBe(2);
  });

  it('describes inspector state for null and selected nodes', () => {
    expect(galaxyInspectorCopy(null).title).toBe('Node inspector');
    expect(galaxyInspectorCopy(null).body).toContain('workspace');
    expect(galaxyInspectorCopy(snapshot.nodes[3]).hint).toContain('prove-source');
    expect(galaxyInspectorCopy(snapshot.nodes[1]).hint).toContain('opens evidence');
  });

  it('resolves workspace navigation targets from hub clicks', () => {
    expect(resolveGalaxyWorkspaceNavigation('workspace_dashpro')).toEqual({
      workspaceId: 'workspace_dashpro',
    });
    expect(resolveGalaxyWorkspaceNavigation('  ')).toBeNull();
    expect(resolveGalaxyWorkspaceNavigation(null)).toBeNull();
  });

  it('builds omnibar hints from run and approval state', () => {
    expect(
      galaxyOmnibarHint({ hasActiveRun: false, runSummary: null, pendingApprovals: 2 }),
    ).toContain('approval');
  });
});
