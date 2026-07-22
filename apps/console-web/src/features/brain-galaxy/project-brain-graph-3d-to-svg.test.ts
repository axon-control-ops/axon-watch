import { describe, expect, it } from 'vitest';

import type { BrainGraphSnapshot } from '../../lib/operator-brain-graph-view';
import { projectBrainGraph3DToSvg } from './project-brain-graph-3d-to-svg';

const snapshot: BrainGraphSnapshot = {
  generated_at: '2026-07-07T21:00:00Z',
  watch_connected: true,
  node_count: 13,
  edge_count: 0,
  nodes: [
    {
      node_id: 'core_kairo',
      kind: 'core',
      label: 'VAXON CORE',
      tone: 'nominal',
      workspace_id: null,
      detail: 'hub',
    },
    ...Array.from({ length: 12 }, (_, index) => ({
      node_id: `ws_${index}`,
      kind: 'workspace' as const,
      label: `WS ${index}`,
      tone: 'nominal' as const,
      workspace_id: `workspace_${index}`,
      detail: 'ok',
    })),
  ],
  edges: [],
};

describe('projectBrainGraph3DToSvg', () => {
  it('projects a labeled nebula cloud instead of a flat radar ring', () => {
    const layout = projectBrainGraph3DToSvg(snapshot, { width: 640, height: 400 });
    const workspaces = layout.nodes.filter((node) => node.kind === 'workspace');
    expect(workspaces.length).toBe(12);
    expect(workspaces.every((node) => node.showLabel)).toBe(true);
    const ys = workspaces.map((node) => node.y);
    const ySpan = Math.max(...ys) - Math.min(...ys);
    expect(ySpan).toBeGreaterThan(60);
    const cx = layout.nebula.cx;
    const cy = layout.nebula.cy;
    const radii = workspaces.map((node) => Math.hypot(node.x - cx, node.y - cy));
    const radiusSpan = Math.max(...radii) - Math.min(...radii);
    expect(radiusSpan).toBeGreaterThan(25);
    expect(layout.nebula.rx).toBeGreaterThan(60);
    expect(layout.stars.length).toBeGreaterThan(20);
  });
});
