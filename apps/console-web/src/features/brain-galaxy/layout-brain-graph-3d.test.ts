import { describe, expect, it } from 'vitest';

import {
  galaxyEdgeColor,
  galaxyNodeColors,
} from './brain-galaxy-colors';
import { layoutBrainGraph3D } from './layout-brain-graph-3d';
import type { BrainGraphSnapshot } from '../../lib/operator-brain-graph-view';

const snapshot: BrainGraphSnapshot = {
  generated_at: '2026-07-07T21:00:00Z',
  watch_connected: true,
  node_count: 5,
  edge_count: 4,
  nodes: [
    {
      node_id: 'core_kairo',
      kind: 'core',
      label: 'KAIRO',
      tone: 'nominal',
      workspace_id: null,
      detail: 'Control plane + watch brain',
    },
    {
      node_id: 'ws_workspace_dashpro',
      kind: 'workspace',
      label: 'DashPro',
      tone: 'attention',
      workspace_id: 'workspace_dashpro',
      detail: '1 active run(s) · 1 signal(s)',
    },
    {
      node_id: 'run_run_abc',
      kind: 'run',
      label: 'git status',
      tone: 'attention',
      workspace_id: 'workspace_dashpro',
      detail: 'review_ready',
    },
    {
      node_id: 'sig_signal_sentry',
      kind: 'signal',
      label: 'Sentry spike',
      tone: 'critical',
      workspace_id: 'workspace_dashpro',
      detail: 'high',
    },
    {
      node_id: 'conn_control_plane',
      kind: 'connector',
      label: 'Control plane',
      tone: 'nominal',
      workspace_id: 'workspace_axon_watch',
      detail: 'ok',
    },
  ],
  edges: [
    { edge_id: 'e1', source: 'core_kairo', target: 'ws_workspace_dashpro', kind: 'member' },
    { edge_id: 'e2', source: 'ws_workspace_dashpro', target: 'run_run_abc', kind: 'executes' },
    { edge_id: 'e3', source: 'ws_workspace_dashpro', target: 'sig_signal_sentry', kind: 'emits' },
    { edge_id: 'e4', source: 'core_kairo', target: 'conn_control_plane', kind: 'monitors' },
  ],
};

describe('layout-brain-graph-3d', () => {
  it('places core at origin', () => {
    const layout = layoutBrainGraph3D(snapshot);
    const core = layout.nodes.find((node) => node.node_id === 'core_kairo');
    expect(core?.x).toBe(0);
    expect(core?.y).toBe(0);
    expect(core?.z).toBe(0);
  });

  it('positions every node and edge endpoint', () => {
    const layout = layoutBrainGraph3D(snapshot);
    expect(layout.nodes).toHaveLength(5);
    expect(layout.edges).toHaveLength(4);
    for (const edge of layout.edges) {
      expect(Number.isFinite(edge.sourcePos.x)).toBe(true);
      expect(Number.isFinite(edge.targetPos.z)).toBe(true);
    }
  });

  it('is deterministic', () => {
    expect(layoutBrainGraph3D(snapshot)).toEqual(layoutBrainGraph3D(snapshot));
  });

  it('spreads nodes in true 3D depth (not a flat radar ring)', () => {
    const layout = layoutBrainGraph3D(snapshot);
    const ys = layout.nodes.map((node) => node.y);
    const span = Math.max(...ys) - Math.min(...ys);
    expect(span).toBeGreaterThan(1.2);
  });

  it('returns empty layout for null snapshot', () => {
    const layout = layoutBrainGraph3D(null);
    expect(layout.nodes).toHaveLength(0);
    expect(layout.edges).toHaveLength(0);
  });
});

describe('brain-galaxy-colors', () => {
  it('boosts core emissive intensity', () => {
    const core = snapshot.nodes[0];
    const colors = galaxyNodeColors(core);
    expect(colors.emissiveIntensity).toBeGreaterThan(1);
  });

  it('maps edge kinds to distinct hues', () => {
    expect(galaxyEdgeColor('emits')).not.toBe(galaxyEdgeColor('monitors'));
  });
});
