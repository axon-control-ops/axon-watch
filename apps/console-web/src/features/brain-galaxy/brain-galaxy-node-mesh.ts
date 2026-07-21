import { Color, Mesh, MeshStandardMaterial, SphereGeometry } from 'three';
import { CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

import type { BrainGraphNode } from '../../lib/operator-brain-graph-view';
import { galaxyNodeColors } from './brain-galaxy-colors';
import type { PositionedBrainNode3D } from './layout-brain-graph-3d';
import { decorateVaxonCoreOrb } from './vaxon-core-orb-3d';
import { decorateWorkspaceNode } from './workspace-node-effects';

export type GalaxyNodeUserData = {
  node: BrainGraphNode;
  originY: number;
};

export type GalaxyNodeMesh = Mesh<SphereGeometry, MeshStandardMaterial> & {
  userData: GalaxyNodeUserData;
};

export function buildGalaxyNodeMesh(node: PositionedBrainNode3D): GalaxyNodeMesh {
  const colors = galaxyNodeColors(node);
  const geometry = new SphereGeometry(
    node.radius,
    node.kind === 'core' ? 48 : 24,
    node.kind === 'core' ? 48 : 24,
  );
  const material = new MeshStandardMaterial({
    color: colors.base,
    emissive: new Color(colors.emissive),
    emissiveIntensity: colors.emissiveIntensity,
    metalness: 0.35,
    roughness: 0.4,
  });
  const mesh = new Mesh(geometry, material);
  mesh.position.set(node.x, node.y, node.z);
  (mesh.userData as GalaxyNodeUserData) = { node, originY: node.y };

  if (node.kind === 'core') {
    decorateVaxonCoreOrb(mesh, node.radius, colors);
  } else if (node.kind === 'workspace') {
    decorateWorkspaceNode(mesh, node.radius, colors, node.x * 1.7 + node.z * 1.3);
  }

  if (node.kind === 'core' || node.kind === 'workspace') {
    const label = document.createElement('span');
    label.className = 'brain-galaxy-node-label';
    if (node.tone === 'attention') {
      label.classList.add('brain-galaxy-node-label--attention');
    }
    if (node.tone === 'critical') {
      label.classList.add('brain-galaxy-node-label--critical');
    }
    if (node.kind === 'core') {
      label.classList.add('brain-galaxy-node-label--core');
      label.textContent = 'VAXON Core';
    } else {
      label.textContent = node.label;
    }
    const labelObject = new CSS2DObject(label);
    labelObject.position.set(0, node.radius + (node.kind === 'core' ? 0.42 : 0.18), 0);
    mesh.add(labelObject);
  }

  return mesh as GalaxyNodeMesh;
}
