import type { OperatorBriefing, RunRecord, RuntimeSummary } from '../../contracts/canonical';
import type { RunHistoryRow } from '../run-history-view';
import { runPhaseProgress, runPhaseTag } from '../mockup-shell-view';
import {
  formatRunDisplayName,
  formatRunIdentityLabel,
  formatRunShortId,
  humanizeRunSummary,
  formatRunCommandDetail,
} from '../run-display';
import type {
  OperatorAgentSummaryItem,
  OperatorExecutionStage,
  OperatorLiveFeedItem,
  OperatorMissionCard,
  OperatorMissionChip,
  OperatorMissionSummary,
  OperatorStatusLoadState,
  OperatorStatusMetricTone,
  OperatorStatusRailItem,
} from './types';
import { firstMeaningfulLine, truncatePanelCopy } from './helpers';
import {
  operatorMissionSummary,
  operatorStatusAdvise,
  operatorStatusHeadline,
} from './core-status';

export function operatorMissionCards(input: {
  runtimeSummary: RuntimeSummary | null;
  briefing: OperatorBriefing | null;
  pendingApprovals: number;
  lastAgentMessage: string | null;
}): OperatorMissionCard[] {
  const openSignals =
    input.briefing?.top_signals.length ?? input.runtimeSummary?.signals.open_count ?? 0;
  const watchConnected =
    input.briefing?.connectivity.watch_connected ?? input.runtimeSummary?.watch.connected ?? false;

  return [
    {
      label: 'Last agent result',
      value: firstMeaningfulLine(input.lastAgentMessage),
      tone: 'default',
    },
    {
      label: 'Runtime summary',
      value: watchConnected ? 'Watch connected · runtime live' : 'Watch disconnected',
      tone: watchConnected ? 'ok' : 'warn',
    },
    {
      label: 'Signals',
      value: openSignals > 0 ? `${openSignals} open attention item(s)` : 'No open signals',
      tone: openSignals > 0 ? 'attention' : 'default',
    },
    {
      label: 'Approval boundary',
      value:
        input.pendingApprovals > 0
          ? `${input.pendingApprovals} approval(s) pending`
          : 'No approval boundary open',
      tone: input.pendingApprovals > 0 ? 'attention' : 'ok',
    },
  ];
}

export function operatorExecutionStage(input: {
  workspaceId: string | null;
  runtimeSummary: RuntimeSummary | null;
  briefing: OperatorBriefing | null;
  loadState: OperatorStatusLoadState;
  primaryActiveRun: RunRecord | null;
  workspaceReviewReadyCount?: number;
  requiredConnectorsUnavailable?: number;
}): OperatorExecutionStage {
  const mission = operatorMissionSummary({
    workspaceId: input.workspaceId,
    runtimeSummary: input.runtimeSummary,
    primaryActiveRun: input.primaryActiveRun,
  });
  const run = input.primaryActiveRun;

  return {
    runId: mission.runId,
    displayName: mission.displayName,
    shortId: mission.shortId,
    identityLabel: mission.identityLabel,
    phase: mission.phase,
    phaseProgress: runPhaseProgress(run?.phase ?? null),
    summary: run ? humanizeRunSummary(run.summary) : 'Standing by for the next command.',
    commandDetail: run ? formatRunCommandDetail(run) : null,
    currentStep: mission.currentStep,
    notice: operatorStatusHeadline({
      briefing: input.briefing,
      loadState: input.loadState,
      primaryActiveRun: run,
      workspaceReviewReadyCount: input.workspaceReviewReadyCount,
      requiredConnectorsUnavailable: input.requiredConnectorsUnavailable,
    }),
    advise: operatorStatusAdvise({
      briefing: input.briefing,
      loadState: input.loadState,
      primaryActiveRun: run,
      requiredConnectorsUnavailable: input.requiredConnectorsUnavailable,
    }),
    decide:
      input.briefing?.executive_rhythm?.decide ??
      'Decide whether to continue from the current operator posture.',
    elapsed: mission.elapsed,
    hasActiveRun: Boolean(run),
  };
}

export function operatorLiveFeed(input: {
  historyRows: RunHistoryRow[];
  currentStep: string | null;
  lastAgentMessage: string | null;
  advise: string;
  hasActiveRun: boolean;
}): OperatorLiveFeedItem[] {
  const items: OperatorLiveFeedItem[] = [];

  for (const row of [...input.historyRows].reverse().slice(-4)) {
    items.push({
      id: row.id,
      label: truncatePanelCopy(row.label, 120),
      meta: row.timestamp,
      tone: 'done',
    });
  }

  if (input.currentStep) {
    items.push({
      id: 'current-step',
      label: truncatePanelCopy(input.currentStep, 120),
      meta: 'Now executing',
      tone: 'active',
    });
  }

  if (input.lastAgentMessage) {
    const excerpt = firstMeaningfulLine(input.lastAgentMessage);
    const alreadyShown = items.some((item) => item.label === excerpt);
    if (!alreadyShown) {
      items.push({
        id: 'agent-output',
        label: excerpt,
        meta: 'Latest agent output',
        tone: 'info',
      });
    }
  }

  if (!input.hasActiveRun && input.advise) {
    items.push({
      id: 'next-action',
      label: truncatePanelCopy(input.advise, 120),
      meta: 'Suggested next step',
      tone: 'pending',
    });
  }

  if (items.length === 0) {
    items.push({
      id: 'idle',
      label: 'No execution activity yet. Send a command from the dock.',
      meta: 'Idle',
      tone: 'pending',
    });
  }

  return items.slice(-6);
}

export function operatorAgentSummary(input: {
  historyRows: RunHistoryRow[];
  currentStep: string | null;
  lastAgentMessage: string | null;
}): OperatorAgentSummaryItem[] {
  const items: OperatorAgentSummaryItem[] = [];

  for (const row of [...input.historyRows].reverse().slice(-3)) {
    items.push({
      id: row.id,
      label: truncatePanelCopy(row.label, 120),
      meta: 'Recorded receipt',
    });
  }

  if (input.currentStep) {
    const current = truncatePanelCopy(input.currentStep, 120);
    if (!items.some((item) => item.label === current)) {
      items.unshift({
        id: 'current-step',
        label: current,
        meta: 'Current step',
      });
    }
  }

  if (input.lastAgentMessage) {
    const excerpt = firstMeaningfulLine(input.lastAgentMessage);
    if (excerpt && !items.some((item) => item.label === excerpt)) {
      items.unshift({
        id: 'agent-output',
        label: excerpt,
        meta: 'Latest agent result',
      });
    }
  }

  if (items.length === 0) {
    items.push({
      id: 'idle',
      label: 'No agent summary yet. Start a run and receipts will accumulate here.',
      meta: 'Idle',
    });
  }

  return items.slice(0, 4);
}

type ConnectorsRailSummary = {
  configured: number;
  ok: number;
  required_unavailable: number;
};

type ConnectorsRailLoadState = 'idle' | 'loading' | 'loaded' | 'error';

function operatorConnectorsRailItem(input: {
  watchConnected: boolean;
  connectorsLoadState: ConnectorsRailLoadState;
  connectorsSummary: ConnectorsRailSummary | null;
}): OperatorStatusRailItem {
  if (!input.watchConnected) {
    return {
      label: 'Connectors',
      value: 'watch offline',
      tone: 'warn',
    };
  }

  if (input.connectorsLoadState === 'loading' || input.connectorsLoadState === 'idle') {
    return {
      label: 'Connectors',
      value: 'loading…',
      tone: 'default',
    };
  }

  if (input.connectorsLoadState === 'error' || !input.connectorsSummary) {
    return {
      label: 'Connectors',
      value: 'unavailable',
      tone: 'warn',
      action: 'focus-connectors',
    };
  }

  const { configured, ok, required_unavailable: requiredDown } = input.connectorsSummary;
  if (requiredDown > 0) {
    return {
      label: 'Connectors',
      value: requiredDown === 1 ? '1 req down' : `${requiredDown} req down`,
      tone: 'attention',
      action: 'focus-connectors',
    };
  }

  return {
    label: 'Connectors',
    value: `${ok}/${configured} ok`,
    tone: 'ok',
    action: 'focus-connectors',
  };
}

export function operatorStatusRail(input: {
  workspaceId: string | null;
  runtimeSummary: RuntimeSummary | null;
  briefing: OperatorBriefing | null;
  pendingApprovals: number;
  connectorsLoadState?: ConnectorsRailLoadState;
  connectorsSummary?: ConnectorsRailSummary | null;
}): OperatorStatusRailItem[] {
  const watchConnected =
    input.briefing?.connectivity.watch_connected ?? input.runtimeSummary?.watch.connected ?? false;
  const controlPlaneReady =
    input.briefing?.connectivity.control_plane_ready ??
    input.runtimeSummary?.control_plane.ready ??
    false;
  const openSignals =
    input.briefing?.top_signals.length ?? input.runtimeSummary?.signals.open_count ?? 0;

  return [
    {
      label: 'Watch',
      value: watchConnected ? 'online' : 'offline',
      tone: watchConnected ? 'ok' : 'warn',
    },
    operatorConnectorsRailItem({
      watchConnected,
      connectorsLoadState: input.connectorsLoadState ?? 'idle',
      connectorsSummary: input.connectorsSummary ?? null,
    }),
    {
      label: 'Signals',
      value: String(openSignals),
      tone: openSignals > 0 ? 'attention' : 'default',
    },
    {
      label: 'Approvals',
      value: String(input.pendingApprovals),
      tone: input.pendingApprovals > 0 ? 'attention' : 'default',
    },
    {
      label: 'Control plane',
      value: controlPlaneReady ? 'ready' : 'not ready',
      tone: controlPlaneReady ? 'ok' : 'warn',
    },
    {
      label: 'Workspace',
      value: input.workspaceId ?? 'none selected',
      tone: input.workspaceId ? 'default' : 'warn',
    },
  ];
}

export function operatorMissionChips(input: {
  lastReceipt: string | null;
  advise: string;
  runtimeSummary: RuntimeSummary | null;
  briefing: OperatorBriefing | null;
  pendingApprovals: number;
  requiredConnectorsUnavailable?: number;
}): OperatorMissionChip[] {
  const openSignals =
    input.briefing?.top_signals.length ?? input.runtimeSummary?.signals.open_count ?? 0;
  const requiredConnectorsUnavailable = input.requiredConnectorsUnavailable ?? 0;
  const risk =
    input.briefing?.degraded.active || input.runtimeSummary?.degraded.active
      ? 'Runtime degraded'
      : requiredConnectorsUnavailable > 0
        ? 'Required connector down'
        : input.pendingApprovals > 0
          ? 'Approval boundary open'
          : openSignals > 0
            ? 'Open signal requires review'
            : 'Nominal';

  return [
    {
      label: 'Last action',
      value: truncatePanelCopy(input.lastReceipt ?? 'No receipts yet', 68),
      tone: 'default',
    },
    {
      label: 'Next action',
      value: truncatePanelCopy(input.advise || 'Await operator input', 68),
      tone: 'warn',
    },
    {
      label: 'Risk',
      value: risk,
      tone: risk === 'Nominal' ? 'ok' : 'attention',
    },
  ];
}
