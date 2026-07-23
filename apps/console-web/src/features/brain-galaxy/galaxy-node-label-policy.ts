import type { BrainGraphNode } from '../../lib/operator-brain-graph-view';

/**
 * Every workspace keeps a name chip. The old parity skip hid ~half of nominal
 * orbs (including the selected workspace), which made the cluster unreadable.
 */
export function shouldShowGalaxyNodeLabel(node: BrainGraphNode): boolean {
  if (node.kind === 'core') {
    return true;
  }
  if (node.kind === 'workspace') {
    return Boolean(String(node.label || '').trim());
  }
  return false;
}
