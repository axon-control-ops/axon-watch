import { Line, Mesh, MeshStandardMaterial } from 'three';
import { CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

import type { BrainGraphNode } from '../../lib/operator-brain-graph-view';
import { galaxyNodeColors } from './brain-galaxy-colors';
import type { PositionedBrainEdge3D } from './layout-brain-graph-3d';
import { setLiveEdgeFocus } from './network-edge-effects';

type SelectableNodeMesh = Mesh & {
  userData: {
    node: BrainGraphNode;
  };
};

export type GalaxySelectionFocus = {
  selectedWorkspaceId: string | null;
  focusedNodeIds: Set<string>;
};

export function applyGalaxySelectionFocus(
  nodeMeshes: SelectableNodeMesh[],
  liveEdges: Line[],
  layoutEdges: PositionedBrainEdge3D[],
  selectedNodeId: string | null,
): GalaxySelectionFocus {
  const selectedNode =
    nodeMeshes.find((mesh) => mesh.userData.node.node_id === selectedNodeId)?.userData.node ?? null;
  const selectedWorkspaceId = selectedNode?.kind === 'workspace' ? selectedNode.node_id : null;
  const focusedNodeIds = connectedNodeIds(layoutEdges, selectedWorkspaceId);

  for (const mesh of nodeMeshes) {
    const material = mesh.material as MeshStandardMaterial;
    const isSelected = Boolean(selectedNodeId && mesh.userData.node.node_id === selectedNodeId);
    const focusStrength =
      !selectedWorkspaceId || focusedNodeIds.has(mesh.userData.node.node_id) ? 1 : 0.16;
    const baseIntensity = galaxyNodeColors(mesh.userData.node).emissiveIntensity;
    material.emissiveIntensity = (isSelected ? baseIntensity + 0.85 : baseIntensity) * focusStrength;
    material.transparent = focusStrength < 1;
    material.opacity = focusStrength;
    material.depthWrite = focusStrength >= 1;
    mesh.traverse((child) => {
      if (child instanceof CSS2DObject) {
        child.element.style.opacity = String(Math.max(focusStrength, 0.62));
        child.element.classList.toggle('brain-galaxy-node-label--selected', isSelected);
      }
    });
  }

  liveEdges.forEach((edge) => setLiveEdgeFocus(edge, selectedWorkspaceId));
  return { selectedWorkspaceId, focusedNodeIds };
}

function connectedNodeIds(
  edges: PositionedBrainEdge3D[],
  selectedWorkspaceId: string | null,
): Set<string> {
  const nodeIds = new Set<string>();
  if (!selectedWorkspaceId) {
    return nodeIds;
  }
  nodeIds.add(selectedWorkspaceId);
  for (const edge of edges) {
    if (edge.source === selectedWorkspaceId || edge.target === selectedWorkspaceId) {
      nodeIds.add(edge.source);
      nodeIds.add(edge.target);
    }
  }
  return nodeIds;
}
