import { describe, expect, it } from 'vitest';

import { galaxyMockupRailItems } from './galaxy-mockup-rail-view';
import type { BrainGraphSnapshot } from '../../lib/operator-brain-graph-view';

describe('galaxyMockupRailItems', () => {
  it('puts VAXON core first and maps workspace stats', () => {
    const snapshot: BrainGraphSnapshot = {
      generated_at: '2026-07-13T00:00:00Z',
      watch_connected: true,
      node_count: 21,
      edge_count: 30,
      nodes: [
        {
          node_id: 'core_kairo',
          kind: 'core',
          label: 'VAXON Core',
          tone: 'nominal',
          workspace_id: null,
          detail: 'core',
        },
        {
          node_id: 'ws_workspace_dashpro',
          kind: 'workspace',
          label: 'DashPro',
          tone: 'attention',
          workspace_id: 'workspace_dashpro',
          detail: 'ws',
        },
        {
          node_id: 'run_1',
          kind: 'run',
          label: 'Run',
          tone: 'nominal',
          workspace_id: 'workspace_dashpro',
          detail: 'run',
        },
      ],
      edges: [
        { edge_id: 'e1', source: 'core_kairo', target: 'ws_workspace_dashpro', kind: 'owns' },
        { edge_id: 'e2', source: 'ws_workspace_dashpro', target: 'run_1', kind: 'run' },
      ],
    };

    const items = galaxyMockupRailItems(snapshot, [
      {
        workspace_id: 'workspace_dashpro',
        display_name: 'DashPro',
        connection_kind: 'project_path',
        project_path: '/tmp/dashpro',
        status: 'ready',
      } as never,
    ]);

    expect(items[0]?.kind).toBe('core');
    expect(items[0]?.detail).toContain('21 nodes');
    expect(items[1]?.label).toBe('DashPro');
    expect(items[1]?.detail).toMatch(/nodes · .*links/);
  });
});
