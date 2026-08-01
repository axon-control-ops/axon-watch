import { computed, type ComputedRef, type Ref } from 'vue';

import type { ConnectorProbeRecord } from '../../../api/control-plane';
import type { RuntimeStatusSnapshot } from '../../../api/runtime-api';
import type {
  InboxItem,
  OperatorBriefing,
  RunRecord,
  RuntimeSummary,
  WorkspaceRecord,
} from '../../../contracts/canonical';
import { buildStatusBarConnectorChip } from '../../../lib/connector-glance-view';
import { buildStatusBarUsageZone } from '../../../lib/cursor-usage-view';
import { shouldShowIdeAgentStop } from '../../../lib/ide-agent-run-active';
import { resolveIdeStopRun } from '../../../lib/ide-composer-queue';
import {
  filterTopbarChipsForIde,
  type IdePresenceProfile,
} from '../../../lib/ide-presence-profile';
import { leftSidebarAttentionBadgeCount as computeLeftSidebarAttentionBadgeCount } from '../../../lib/left-sidebar-mode';
import {
  buildBriefingSummaryLine,
  buildStatusBarZones,
  buildTopbarBreadcrumb,
  buildTopbarMetaPills,
  buildWorkspaceStatusCardRows,
} from '../../../lib/mockup-shell-view';
import { conversationEmptyStateLabel, type OperatorThreadEntry } from '../../../lib/operator-thread';
import { resolveOperatorSignalCount, resolveAttentionSignalCount, filterAttentionSignals } from '../../../lib/operator-signal-count';
import { workspaceCatalogMode } from '../../../lib/operator-workspace-catalog';
import { formatRunIdentityLabel } from '../../../lib/run-display';
import {
  isOperatorCompletablePhase,
  shouldOfferRunContinue,
} from '../../../lib/run-lifecycle-ui';
import { buildStatusBarSegments, buildTopbarChips } from '../../../lib/runtime-strip';
import { selectPrimaryApprovalRun } from '../../shell-run-selection';
import type {
  InboxLoadState,
  LayoutMode,
  RunMutationState,
  RunsLoadState,
  RuntimeSummaryLoadState,
} from '../types';

interface CreateShellDisplaySliceInput {
  currentWorkspace: Ref<WorkspaceRecord | null>;
  workspaces: Ref<WorkspaceRecord[]>;
  runtimeSummary: Ref<RuntimeSummary | null>;
  runtimeSummaryLoadState: Ref<RuntimeSummaryLoadState>;
  runtimeStatus: Ref<RuntimeStatusSnapshot | null>;
  primaryActiveRun: ComputedRef<RunRecord | null>;
  layoutMode: Ref<LayoutMode>;
  getIdePresenceProfile: () => IdePresenceProfile;
  inboxItems: Ref<InboxItem[]>;
  inboxLoadState: Ref<InboxLoadState>;
  operatorBriefing: Ref<OperatorBriefing | null>;
  runs: Ref<RunRecord[]>;
  runsLoadState: Ref<RunsLoadState>;
  runMutationState: Ref<RunMutationState>;
  ideAgentLinkedRun: ComputedRef<RunRecord | null>;
  ideAgentRunId: Ref<string | null>;
  agentStreamActive: Ref<boolean>;
  operatorThreadMessages: Ref<OperatorThreadEntry[]>;
  threadMessages: Ref<OperatorThreadEntry[]>;
  connectorsItems: Ref<ConnectorProbeRecord[]>;
  connectorsSummary: Ref<{ required_unavailable: number } | null>;
  connectorsLoadState: Ref<'idle' | 'loading' | 'loaded' | 'error'>;
  /** Kept for callers that still pass fleet activeRun; unused by status-bar zones. */
  activeRun?: Ref<RunRecord | null>;
}

export function createShellDisplaySlice(input: CreateShellDisplaySliceInput) {
  const workspaceTrailLabel = computed(() => {
    const workspace = input.currentWorkspace.value?.workspace_id ?? 'No workspace selected';
    const identity = input.runtimeSummary.value?.runtime_identity;
    if (!identity) {
      return workspace;
    }
    return `${workspace} / ${identity.provider_name}`;
  });

  const workspaceStateLabel = computed(() => {
    if (!input.currentWorkspace.value) {
      return 'No workspace selected';
    }
    return (
      input.currentWorkspace.value.display_name?.trim() ||
      input.currentWorkspace.value.workspace_id
    );
  });

  const usesProductionWorkspaceCatalog = computed(
    () => workspaceCatalogMode(input.workspaces.value) === 'production',
  );

  const topbarChips = computed(() => {
    const chips = buildTopbarChips({
      runtimeSummary: input.runtimeSummary.value,
      runtimeSummaryLoadState: input.runtimeSummaryLoadState.value,
      // Workspace-scoped primary only — fleet `activeRun` caused stale Resume chips while IDLE.
      primaryActiveRun: input.primaryActiveRun.value,
    });
    return filterTopbarChipsForIde(
      chips,
      input.layoutMode.value,
      input.getIdePresenceProfile(),
    );
  });

  const topbarMetaPills = computed(() => buildTopbarMetaPills(input.runtimeSummary.value));
  const topbarBreadcrumb = computed(() =>
    buildTopbarBreadcrumb(input.runtimeSummary.value, input.currentWorkspace.value),
  );

  const activeOperatorSignalCount = computed(() =>
    resolveOperatorSignalCount({
      inboxItems: input.inboxItems.value,
      inboxLoadState: input.inboxLoadState.value,
      runtimeSummaryOpenCount: input.runtimeSummary.value?.signals.open_count,
    }),
  );

  const attentionSignals = computed(() => {
    const workspaceId = input.currentWorkspace.value?.workspace_id ?? null;
    const fromInbox =
      input.inboxLoadState.value === 'loaded' ||
      (input.inboxLoadState.value === 'loading' && input.inboxItems.value.length > 0)
        ? filterAttentionSignals(input.inboxItems.value, workspaceId)
        : [];
    // Loaded-but-empty inbox was blanking Mission Control Attention while
    // briefing still had actionable top signals (Sentry / CI / Android).
    const fromBriefing = filterAttentionSignals(
      input.operatorBriefing.value?.top_signals ?? [],
      workspaceId,
    );
    const items = fromInbox.length > 0 ? fromInbox : fromBriefing;
    return items.slice(0, 3);
  });

  const workspaceAttentionSignalCount = computed(() =>
    resolveAttentionSignalCount({
      inboxItems: input.inboxItems.value,
      inboxLoadState: input.inboxLoadState.value,
      runtimeSummaryOpenCount: input.runtimeSummary.value?.signals.open_count,
      workspaceId: input.currentWorkspace.value?.workspace_id ?? null,
      briefingTopSignals: input.operatorBriefing.value?.top_signals ?? null,
    }),
  );

  const statusBarZones = computed(() => {
    const zones = buildStatusBarZones({
      runtimeSummary: input.runtimeSummary.value,
      runtimeSummaryLoadState: input.runtimeSummaryLoadState.value,
      primaryActiveRun: input.primaryActiveRun.value,
      workspaceId: input.currentWorkspace.value?.workspace_id ?? null,
      layoutMode: input.layoutMode.value,
      idePresenceProfile: input.getIdePresenceProfile(),
      activeSignalCount: activeOperatorSignalCount.value,
    });

    const watchConnected = input.runtimeSummary.value?.watch.connected ?? false;
    const connectorChipInput = {
      connectorsLoadState: input.connectorsLoadState.value,
      items: input.connectorsItems.value,
      summary: input.connectorsSummary.value,
      watchConnected,
      layoutMode: input.layoutMode.value,
    };
    const connectorChip = buildStatusBarConnectorChip(connectorChipInput);
    if (connectorChip) {
      zones.center.push(connectorChip);
    }

    const usageZone = buildStatusBarUsageZone(input.runtimeStatus.value?.cursor_usage);
    if (usageZone) {
      zones.center.push(usageZone);
    }

    return zones;
  });

  const layoutModeLabel = computed(() =>
    input.layoutMode.value === 'operator' ? 'Mission Control' : 'IDE mode',
  );

  const statusBarSegments = computed(() =>
    buildStatusBarSegments({
      layoutModeLabel: layoutModeLabel.value,
      workspaceId: input.currentWorkspace.value?.workspace_id ?? null,
      runtimeSummary: input.runtimeSummary.value,
      pendingApprovals: pendingApprovalsCount.value,
    }),
  );

  const statusBarItems = computed(() => statusBarSegments.value.map((segment) => segment.label));

  const workspaceStatusCardRows = computed(() =>
    buildWorkspaceStatusCardRows({
      runtimeSummary: input.runtimeSummary.value,
      runtimeSummaryLoadState: input.runtimeSummaryLoadState.value,
    }),
  );

  const briefingSummaryLine = computed(() =>
    buildBriefingSummaryLine(
      input.operatorBriefing.value,
      input.runtimeSummary.value,
      input.currentWorkspace.value?.workspace_id ?? null,
      activeOperatorSignalCount.value,
    ),
  );

  const runtimeStateLabel = computed(() =>
    topbarChips.value.map((chip) => chip.label).join(' · '),
  );

  const runStateLabel = computed(() => {
    if (input.runsLoadState.value === 'loading') {
      return 'Loading active run…';
    }

    if (input.runsLoadState.value === 'error') {
      return 'Active run unavailable';
    }

    if (!input.primaryActiveRun.value) {
      return 'No active run';
    }

    return formatRunIdentityLabel(input.primaryActiveRun.value);
  });

  const runMutationPending = computed(() => input.runMutationState.value !== 'idle');

  const activeIdeStopRun = computed(() =>
    resolveIdeStopRun({
      linkedRun: input.ideAgentLinkedRun.value,
      linkedRunId: input.ideAgentRunId.value,
      runs: input.runs.value,
      primaryRun: input.primaryActiveRun.value,
      workspaceId: input.currentWorkspace.value?.workspace_id ?? null,
    }),
  );

  const canStopIdeAgentRun = computed(() => {
    if (runMutationPending.value) {
      return false;
    }
    // Stream-live only. Idle executing runs surface Resume/Continue, not Stop.
    return shouldShowIdeAgentStop({
      agentStreamActive: input.agentStreamActive.value,
      run: input.ideAgentLinkedRun.value ?? activeIdeStopRun.value,
    });
  });

  const canStopPrimaryRun = computed(
    () => Boolean(input.primaryActiveRun.value?.can_stop) && !runMutationPending.value,
  );
  const canResumePrimaryRun = computed(() => {
    const run = input.primaryActiveRun.value;
    if (!run || runMutationPending.value) {
      return false;
    }
    return shouldOfferRunContinue({
      phase: run.phase,
      canResume: Boolean(run.can_resume),
      agentStreamActive: input.agentStreamActive.value,
      mode: run.mode,
    });
  });
  const canMarkPrimaryRunReviewReady = computed(
    () => input.primaryActiveRun.value?.phase === 'executing' && !runMutationPending.value,
  );
  const canCompletePrimaryRun = computed(
    () =>
      isOperatorCompletablePhase(input.primaryActiveRun.value?.phase) &&
      !runMutationPending.value,
  );

  const primaryApprovalRun = computed(() => selectPrimaryApprovalRun(input.runs.value));
  const primaryInboxItem = computed(() => input.inboxItems.value[0] ?? null);

  const inboxStateLabel = computed(() => {
    if (input.inboxLoadState.value === 'loading') {
      return 'Loading signals…';
    }

    if (input.inboxLoadState.value === 'error') {
      return 'Signals unavailable';
    }

    const primary = input.inboxItems.value[0];
    if (!primary) {
      return 'No open signals';
    }

    return `${primary.title} · ${primary.severity}`;
  });

  const approvalsSummaryLabel = computed(() => {
    const pending =
      input.runtimeSummary.value?.approvals.pending_count ??
      input.operatorBriefing.value?.pending_approvals.count ??
      0;
    if (pending === 0) {
      return 'Nothing waiting for your yes or no';
    }
    return `${pending} job${pending === 1 ? '' : 's'} waiting for your yes or no`;
  });

  const canApprovePrimaryRun = computed(
    () => Boolean(primaryApprovalRun.value?.can_approve) && !runMutationPending.value,
  );
  const canApproveIdeAgentRun = computed(
    () => Boolean(input.ideAgentLinkedRun.value?.can_approve) && !runMutationPending.value,
  );
  const canResumeIdeAgentRun = computed(() => {
    const run = input.ideAgentLinkedRun.value;
    if (!run || runMutationPending.value) {
      return false;
    }
    return shouldOfferRunContinue({
      phase: run.phase,
      canResume: Boolean(run.can_resume),
      agentStreamActive: input.agentStreamActive.value,
      mode: run.mode,
    });
  });
  const canRejectPrimaryRun = computed(
    () =>
      primaryApprovalRun.value?.phase === 'awaiting_approval' && !runMutationPending.value,
  );

  const threadStateLabel = computed(() =>
    conversationEmptyStateLabel(
      (input.layoutMode.value === 'operator'
        ? input.operatorThreadMessages.value
        : input.threadMessages.value
      ).length,
    ),
  );

  const pendingApprovalsCount = computed(() => {
    const fromSummary = input.runtimeSummary.value?.approvals.pending_count ?? 0;
    const fromBriefing = input.operatorBriefing.value?.pending_approvals.count ?? 0;
    return Math.max(fromSummary, fromBriefing);
  });

  const leftSidebarAttentionBadgeCount = computed(() => {
    const workspaceId = input.currentWorkspace.value?.workspace_id;
    const reviewReadyCount = input.runs.value.filter(
      (run) =>
        run.phase === 'review_ready' &&
        (!workspaceId || run.workspace_id === workspaceId),
    ).length;
    return computeLeftSidebarAttentionBadgeCount({
      pendingApprovals: pendingApprovalsCount.value,
      briefing: input.operatorBriefing.value,
      inboxItems: input.inboxItems.value,
      inboxLoadState: input.inboxLoadState.value,
      reviewReadyCount,
    });
  });

  return {
    workspaceTrailLabel,
    workspaceStateLabel,
    usesProductionWorkspaceCatalog,
    topbarChips,
    topbarMetaPills,
    topbarBreadcrumb,
    activeOperatorSignalCount,
    attentionSignals,
    workspaceAttentionSignalCount,
    statusBarZones,
    statusBarSegments,
    statusBarItems,
    layoutModeLabel,
    workspaceStatusCardRows,
    briefingSummaryLine,
    runtimeStateLabel,
    runStateLabel,
    runMutationPending,
    activeIdeStopRun,
    canStopIdeAgentRun,
    canStopPrimaryRun,
    canResumePrimaryRun,
    canMarkPrimaryRunReviewReady,
    canCompletePrimaryRun,
    primaryApprovalRun,
    primaryInboxItem,
    inboxStateLabel,
    approvalsSummaryLabel,
    canApprovePrimaryRun,
    canApproveIdeAgentRun,
    canResumeIdeAgentRun,
    canRejectPrimaryRun,
    threadStateLabel,
    pendingApprovalsCount,
    leftSidebarAttentionBadgeCount,
  };
}
