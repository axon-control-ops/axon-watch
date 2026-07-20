import type { ConnectorProbeRecord } from '../api/control-plane';

import {
  agentDockReopenAlive,
  agentDockReopenAriaLabel,
  agentDockReopenEmployeeFailure,
  agentDockReopenEmployeeInterrupted,
  agentDockReopenTitle,
  type AgentDockReopenState,
} from './agent-dock-reopen-view';
import {
  buildConnectorGlanceChip,
  buildRequiredConnectorAlertChip,
  type ConnectorStatusBarChip,
  type ConnectorStatusBarChipId,
} from './connector-glance-view';
import {
  workbenchTerminalPanelAlive,
  workbenchTerminalPanelAriaLabel,
  workbenchTerminalPanelTitle,
} from './workbench-terminal-panel-view';

export type IdeEditorStatusConnectorChip = {
  id: ConnectorStatusBarChipId;
  label: string;
  tone: ConnectorStatusBarChip['tone'];
  title: string;
  ariaLabel: string;
};

type IdeEditorStatusConnectorChipInput = {
  connectorsLoadState: 'idle' | 'loading' | 'loaded' | 'error';
  items: readonly ConnectorProbeRecord[];
  summary: { required_unavailable: number } | null;
  watchConnected: boolean;
};

function shortConnectorLabel(
  chip: ConnectorStatusBarChip,
  requiredUnavailable: number,
): string {
  if (chip.id === 'connector-required-alert') {
    return requiredUnavailable === 1 ? '1 REQ DOWN' : `${requiredUnavailable} REQ DOWN`;
  }

  if (chip.label.includes('DEGRADED')) {
    return 'LEGACY DEGRADED';
  }

  return 'LEGACY OFFLINE';
}

function connectorChipTitle(id: ConnectorStatusBarChipId): string {
  if (id === 'connector-required-alert') {
    return 'Required connector down — switch to Mission Control connectors';
  }

  return 'Legacy connector offline — switch to Mission Control connectors';
}

function connectorChipAriaLabel(id: ConnectorStatusBarChipId, label: string): string {
  return `${label}. ${connectorChipTitle(id)}.`;
}

/** Compact connector chip for the IDE editor status bar (footer chips stay verbose). */
export function buildIdeEditorStatusConnectorChip(
  input: IdeEditorStatusConnectorChipInput,
): IdeEditorStatusConnectorChip | null {
  if (!input.watchConnected) {
    const title =
      'Watch offline — connector probes paused until the watch reconnects';
    return {
      id: 'watch-offline',
      label: 'WATCH OFFLINE',
      tone: 'warning',
      title,
      ariaLabel: `WATCH OFFLINE. ${title}.`,
    };
  }

  const chipInput = {
    ...input,
    layoutMode: 'ide' as const,
  };
  const requiredUnavailable = input.summary?.required_unavailable ?? 0;
  const chip =
    buildRequiredConnectorAlertChip(chipInput) ?? buildConnectorGlanceChip(chipInput);
  if (!chip) {
    return null;
  }

  const label = shortConnectorLabel(chip, requiredUnavailable);
  const title = connectorChipTitle(chip.id);

  return {
    id: chip.id,
    label,
    tone: chip.tone,
    title,
    ariaLabel: connectorChipAriaLabel(chip.id, label),
  };
}

export type IdeEditorStatusTerminalChip = {
  label: 'TERMINAL';
  title: string;
  ariaLabel: string;
  showPulse: boolean;
  executing: boolean;
  reviewReady: boolean;
};

/** Terminal reopen chip for the IDE editor status bar when the panel is hidden. */
export function buildIdeEditorStatusTerminalChip(input: {
  terminalVisible: boolean;
  runPhase: string | null;
}): IdeEditorStatusTerminalChip | null {
  if (input.terminalVisible) {
    return null;
  }

  const runPhase = input.runPhase ?? null;

  return {
    label: 'TERMINAL',
    title: workbenchTerminalPanelTitle(false, runPhase),
    ariaLabel: workbenchTerminalPanelAriaLabel(false, runPhase),
    showPulse: workbenchTerminalPanelAlive(runPhase),
    executing: runPhase === 'executing',
    reviewReady: runPhase === 'review_ready',
  };
}

export type IdeEditorStatusAgentChip = {
  label: 'AGENT';
  title: string;
  ariaLabel: string;
  showPulse: boolean;
  showBadge: number | null;
  alive: boolean;
  streaming: boolean;
  approvals: boolean;
  executing: boolean;
  reviewReady: boolean;
  failure: boolean;
  interrupted: boolean;
};

/** Agent reopen chip for the IDE editor status bar when the dock is collapsed. */
export function buildIdeEditorStatusAgentChip(input: {
  agentDockCollapsed: boolean;
  state: AgentDockReopenState;
}): IdeEditorStatusAgentChip | null {
  if (!input.agentDockCollapsed) {
    return null;
  }

  const { state } = input;
  const pendingApprovals = state.pendingApprovals;
  const runPhase = state.runPhase ?? null;
  const alive = agentDockReopenAlive(state);
  const failure = agentDockReopenEmployeeFailure(state);
  const interrupted = agentDockReopenEmployeeInterrupted(state);

  return {
    label: 'AGENT',
    title: agentDockReopenTitle(state),
    ariaLabel: agentDockReopenAriaLabel(state),
    showPulse: alive && pendingApprovals <= 0,
    showBadge: pendingApprovals > 0 ? pendingApprovals : null,
    alive,
    streaming: state.streaming,
    approvals: pendingApprovals > 0,
    executing: runPhase === 'executing',
    reviewReady: runPhase === 'review_ready',
    failure,
    interrupted,
  };
}
