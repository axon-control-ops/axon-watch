import type { BrainGraphNode } from '../../lib/operator-brain-graph-view';
import { resolveGalaxyWorkspaceNavigation } from './brain-galaxy-hud-view';

type GalaxyEvidenceShell = {
  focusAttentionSidebar: (signalId: string) => void;
  handoffSignalToIde: (
    signal: {
      signal_id: string;
      workspace_id?: string | null;
      title: string;
      summary?: string | null;
      meta?: Record<string, unknown> | null;
    },
    options: { autoSubmit: boolean },
  ) => Promise<void> | void;
};

export function openGalaxyEvidenceWorkspace(input: {
  workspaceId: string;
  selectedNode: BrainGraphNode | null;
  fallbackLabel: string;
  enterWorkspace: (workspaceId: string, nodeId: string, label: string) => void;
}): void {
  const nav = resolveGalaxyWorkspaceNavigation(input.workspaceId);
  if (!nav) {
    return;
  }
  const label = input.selectedNode?.label ?? input.fallbackLabel;
  input.enterWorkspace(nav.workspaceId, `ws_${input.workspaceId}`, label);
}

export function focusGalaxyEvidenceSignal(
  shell: GalaxyEvidenceShell,
  signalId: string,
): void {
  shell.focusAttentionSidebar(signalId);
}

export function handoffGalaxyEvidenceSignal(
  shell: GalaxyEvidenceShell,
  signal: {
    signal_id: string;
    workspace_id?: string | null;
    title: string;
    summary?: string | null;
    meta?: Record<string, unknown> | null;
  },
): void {
  void shell.handoffSignalToIde(signal, { autoSubmit: true });
}
