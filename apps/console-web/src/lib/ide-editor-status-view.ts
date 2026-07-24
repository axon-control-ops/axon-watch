import type { ConnectorProbeRecord } from '../api/control-plane';
import type { CompanyEmployeeRecord } from '../contracts/canonical';
import {
  buildCompanyRosterAlertBadge,
  companyFailedEmployees,
  type CompanyRosterAlertBadgeTone,
} from '../features/workspace-agents/company-roster-failure-view';

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
  ideActivityBarGitAttentionHint,
  ideActivityBarSearchAttentionHint,
} from './ide-activity-bar-view';
import type { IdeSearchPanelLoadState } from './ide-activity-panel-view';
import { shouldShowIdeSearchPanelAttention } from './ide-activity-panel-view';
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

  if (id === 'watch-offline') {
    return 'Watch offline — connector probes paused until the watch reconnects';
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
  label: 'AGENT' | 'SPEAKING';
  title: string;
  ariaLabel: string;
  showPulse: boolean;
  showBadge: number | null;
  alive: boolean;
  streaming: boolean;
  speaking: boolean;
  approvals: boolean;
  executing: boolean;
  reviewReady: boolean;
  failure: boolean;
  interrupted: boolean;
};

export type IdeEditorStatusGitChip = {
  label: string;
  title: string;
  ariaLabel: string;
  count: number;
};

export type IdeEditorStatusSearchChip = {
  label: 'SEARCH ERR';
  title: string;
  ariaLabel: string;
};

export type IdeEditorStatusTeamChip = {
  label: string;
  title: string;
  ariaLabel: string;
  tone: CompanyRosterAlertBadgeTone;
  count: number;
};

function teamChipLabel(count: number, tone: CompanyRosterAlertBadgeTone): string {
  if (tone === 'interrupted') {
    return count === 1 ? '1 INTERRUPTED' : `${count} INTERRUPTED`;
  }

  if (tone === 'failure') {
    return count === 1 ? '1 FAILED' : `${count} FAILED`;
  }

  return `${count} NEED ATTENTION`;
}

/** Team chip for the IDE editor status bar when roster teammates need attention. */
export function buildIdeEditorStatusTeamChip(input: {
  employees: readonly CompanyEmployeeRecord[] | null | undefined;
  teamExpanded: boolean;
}): IdeEditorStatusTeamChip | null {
  if (input.teamExpanded) {
    return null;
  }

  const count = companyFailedEmployees(input.employees).length;
  if (count === 0) {
    return null;
  }

  const badge = buildCompanyRosterAlertBadge(input.employees);
  if (!badge) {
    return null;
  }

  const label = teamChipLabel(count, badge.tone);

  return {
    label,
    title: badge.title,
    ariaLabel: `${label}. ${badge.ariaLabel}. Open Team sidebar in the left activity bar.`,
    tone: badge.tone,
    count,
  };
}

/** Source Control chip for the IDE editor status bar when file tabs have unsaved edits. */
export function buildIdeEditorStatusGitChip(input: {
  dirtyFileCount: number;
  sourceControlExpanded: boolean;
}): IdeEditorStatusGitChip | null {
  if (input.sourceControlExpanded || input.dirtyFileCount <= 0) {
    return null;
  }

  const count = input.dirtyFileCount;
  const hint = ideActivityBarGitAttentionHint(count) ?? `${count} unsaved files`;
  const label = count === 1 ? '1 UNSAVED' : `${count} UNSAVED`;
  const title = `Unsaved workspace file tabs — open Source Control sidebar to review`;
  const ariaLabel = `${label}. ${hint}. Open Source Control sidebar in the left activity bar.`;

  return { label, title, ariaLabel, count };
}

/** Search chip for the IDE editor status bar when workspace files fail to load. */
export function buildIdeEditorStatusSearchChip(input: {
  loadState: IdeSearchPanelLoadState;
  hasWorkspace: boolean;
  searchExpanded: boolean;
}): IdeEditorStatusSearchChip | null {
  if (
    input.searchExpanded ||
    !shouldShowIdeSearchPanelAttention({
      loadState: input.loadState,
      hasWorkspace: input.hasWorkspace,
    })
  ) {
    return null;
  }

  const hint =
    ideActivityBarSearchAttentionHint({
      loadState: input.loadState,
      hasWorkspace: input.hasWorkspace,
    }) ?? 'Workspace files failed to load';
  const title = 'Workspace file index failed to load — open Search sidebar to retry';
  const ariaLabel = `SEARCH ERR. ${hint}. Open Search sidebar in the left activity bar.`;

  return { label: 'SEARCH ERR', title, ariaLabel };
}

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
  const speaking = Boolean(state.speaking);
  const alive = agentDockReopenAlive(state);
  const failure = agentDockReopenEmployeeFailure(state);
  const interrupted = agentDockReopenEmployeeInterrupted(state);

  return {
    label: speaking ? 'SPEAKING' : 'AGENT',
    title: agentDockReopenTitle(state),
    ariaLabel: agentDockReopenAriaLabel(state),
    showPulse: alive && pendingApprovals <= 0,
    showBadge: pendingApprovals > 0 ? pendingApprovals : null,
    alive,
    streaming: state.streaming,
    speaking,
    approvals: pendingApprovals > 0,
    executing: runPhase === 'executing',
    reviewReady: runPhase === 'review_ready',
    failure,
    interrupted,
  };
}
