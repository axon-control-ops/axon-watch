import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  brainGraphHeadline,
  layoutBrainGraph,
  readStoredOperatorCenterView,
  type BrainGraphSnapshot,
} from './operator-brain-graph-view';

function memorySessionStorage(): Storage {
  const store = new Map<string, string>();
  return {
    get length() {
      return store.size;
    },
    clear() {
      store.clear();
    },
    getItem(key: string) {
      return store.has(key) ? store.get(key)! : null;
    },
    key(index: number) {
      return [...store.keys()][index] ?? null;
    },
    removeItem(key: string) {
      store.delete(key);
    },
    setItem(key: string, value: string) {
      store.set(key, String(value));
    },
  };
}

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

describe('operator-brain-graph-view', () => {
  it('places core at center and positions every node', () => {
    const layout = layoutBrainGraph(snapshot, { width: 600, height: 400 });

    expect(layout.nodes).toHaveLength(5);
    const core = layout.nodes.find((node) => node.node_id === 'core_kairo');
    expect(core?.x).toBe(300);
    expect(core?.y).toBe(200);
  });

  it('keeps every node inside the viewport', () => {
    const layout = layoutBrainGraph(snapshot, { width: 600, height: 400 });

    for (const node of layout.nodes) {
      expect(node.x).toBeGreaterThanOrEqual(0);
      expect(node.x).toBeLessThanOrEqual(600);
      expect(node.y).toBeGreaterThanOrEqual(0);
      expect(node.y).toBeLessThanOrEqual(400);
    }
  });

  it('positions all edges with resolvable endpoints', () => {
    const layout = layoutBrainGraph(snapshot, { width: 600, height: 400 });

    expect(layout.edges).toHaveLength(4);
    for (const edge of layout.edges) {
      expect(Number.isFinite(edge.x1)).toBe(true);
      expect(Number.isFinite(edge.y2)).toBe(true);
    }
  });

  it('is deterministic for the same snapshot', () => {
    const first = layoutBrainGraph(snapshot);
    const second = layoutBrainGraph(snapshot);
    expect(first).toEqual(second);
  });

  it('returns empty layout for null snapshot', () => {
    const layout = layoutBrainGraph(null);
    expect(layout.nodes).toHaveLength(0);
    expect(layout.edges).toHaveLength(0);
  });

  it('summarizes headline with attention count', () => {
    expect(brainGraphHeadline(snapshot)).toContain('need attention');
    expect(brainGraphHeadline(null)).toContain('Loading');
    expect(
      brainGraphHeadline({ ...snapshot, watch_connected: false }),
    ).toContain('disconnected');
  });

  it('defaults Mission Control fleet when no center view is stored', () => {
    vi.stubGlobal('sessionStorage', memorySessionStorage());
    expect(readStoredOperatorCenterView()).toBe('grid');
  });

  it('restores Brain Graph when sessionStorage says graph', () => {
    const storage = memorySessionStorage();
    storage.setItem('axon.operator.center-view', 'graph');
    vi.stubGlobal('sessionStorage', storage);
    expect(readStoredOperatorCenterView()).toBe('graph');
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });
});
