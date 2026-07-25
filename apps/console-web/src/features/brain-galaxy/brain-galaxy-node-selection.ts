import type { BrainGraphNode } from '../../lib/operator-brain-graph-view';

import type { BrainGalaxyConversationFocus } from './brain-galaxy-focus';

/**
 * Map a brain-galaxy node click into conversation focus + whether the evidence
 * panel should load for this node.
 */
export function resolveBrainGalaxyNodeSelection(
  node: BrainGraphNode | null | undefined,
): {
  focus: BrainGalaxyConversationFocus | null;
  evidenceNodeId: string | null;
} {
  if (!node?.node_id) {
    return { focus: null, evidenceNodeId: null };
  }

  const signalId =
    node.kind === 'signal' ? node.node_id.replace(/^sig_/, '') : null;

  return {
    focus: {
      nodeId: node.node_id,
      workspaceId: node.workspace_id,
      signalId,
      label: node.label || node.node_id,
    },
    evidenceNodeId: node.node_id,
  };
}
