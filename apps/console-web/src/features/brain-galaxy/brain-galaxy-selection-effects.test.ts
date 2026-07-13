import { describe, expect, it } from 'vitest';
import { Mesh, MeshStandardMaterial, SphereGeometry } from 'three';

import { applyGalaxySelectionFocus } from './brain-galaxy-selection-effects';
import { buildLiveEdge } from './network-edge-effects';
import type { BrainGraphNode } from '../../lib/operator-brain-graph-view';
import type { PositionedBrainEdge3D } from './layout-brain-graph-3d';

function node(nodeId: string, kind: string): BrainGraphNode {
  return {
    node_id: nodeId,
    kind,
    label: nodeId,
    tone: 'nominal',
    workspace_id: kind === 'workspace' ? nodeId : null,
    detail: '',
  };
}

function mesh(record: BrainGraphNode): Mesh<SphereGeometry, MeshStandardMaterial> {
  const value = new Mesh(new SphereGeometry(0.2), new MeshStandardMaterial());
  value.userData = { node: record, originY: 0 };
  return value;
}

describe('applyGalaxySelectionFocus', () => {
  it('keeps the selected workspace neighborhood bright and dims unrelated nodes', () => {
    const core = mesh(node('core', 'core'));
    const selected = mesh(node('ws_one', 'workspace'));
    const unrelated = mesh(node('ws_two', 'workspace'));
    const edges: PositionedBrainEdge3D[] = [
      {
        edge_id: 'edge_one',
        source: 'core',
        target: 'ws_one',
        kind: 'contains',
        sourcePos: { x: 0, y: 0, z: 0 },
        targetPos: { x: 1, y: 0, z: 0 },
      },
      {
        edge_id: 'edge_two',
        source: 'core',
        target: 'ws_two',
        kind: 'contains',
        sourcePos: { x: 0, y: 0, z: 0 },
        targetPos: { x: -1, y: 0, z: 0 },
      },
    ];
    const liveEdges = edges.map(buildLiveEdge);

    const focus = applyGalaxySelectionFocus(
      [core, selected, unrelated] as never[],
      liveEdges,
      edges,
      'ws_one',
    );

    expect(focus.selectedWorkspaceId).toBe('ws_one');
    expect(focus.focusedNodeIds).toEqual(new Set(['ws_one', 'core']));
    expect(selected.material.opacity).toBe(1);
    expect(core.material.opacity).toBe(1);
    expect(unrelated.material.opacity).toBe(0.16);
    expect(liveEdges[0]?.userData.focusStrength).toBe(1);
    expect(liveEdges[1]?.userData.focusStrength).toBe(0.12);
  });
});
