import { isBootstrapSummarySignal } from './operator-signal-hints';

export type OperatorSignalCountItem = {
  signal_id: string;
  title: string;
  status?: string | null;
  workspace_id?: string | null;
  severity?: string | null;
  summary?: string | null;
  delivery_state?: string | null;
  latest_receipt_id?: string | null;
  watch_rule?: {
    mode?: string | null;
    reason?: string | null;
    interrupts?: boolean | null;
  } | null;
  meta?: Record<string, unknown> | null;
};

export function isActionableOpenSignal(item: OperatorSignalCountItem): boolean {
  if ((item.status ?? 'open') !== 'open') {
    return false;
  }

  return !isBootstrapSummarySignal(item.signal_id, item.title);
}

export function filterActionableOpenSignals(
  items: OperatorSignalCountItem[],
  workspaceId?: string | null,
): OperatorSignalCountItem[] {
  const scopedWorkspaceId = workspaceId?.trim() ?? '';

  return items.filter((item) => {
    if (!isActionableOpenSignal(item)) {
      return false;
    }

    if (!scopedWorkspaceId) {
      return true;
    }

    const itemWorkspaceId = item.workspace_id?.trim() ?? '';
    return !itemWorkspaceId || itemWorkspaceId === scopedWorkspaceId;
  });
}

export function countActionableOpenSignals(
  items: OperatorSignalCountItem[],
  workspaceId?: string | null,
): number {
  return filterActionableOpenSignals(items, workspaceId).length;
}

function isInterruptiveSeverity(severity?: string | null): boolean {
  const normalized = (severity ?? '').toLowerCase();
  return normalized === 'high' || normalized === 'critical';
}

/**
 * Attention-stack signals: current workspace (or unscoped) plus interruptive
 * high/critical signals from other workspaces so fleet alerts stay actionable.
 */
export function filterAttentionSignals(
  items: OperatorSignalCountItem[],
  workspaceId?: string | null,
): OperatorSignalCountItem[] {
  const scopedWorkspaceId = workspaceId?.trim() ?? '';
  const actionable = filterActionableOpenSignals(items);

  if (!scopedWorkspaceId) {
    return actionable;
  }

  return actionable.filter((item) => {
    const itemWorkspaceId = item.workspace_id?.trim() ?? '';
    if (!itemWorkspaceId || itemWorkspaceId === scopedWorkspaceId) {
      return true;
    }
    return isInterruptiveSeverity(item.severity);
  });
}

export function countAttentionSignals(
  items: OperatorSignalCountItem[],
  workspaceId?: string | null,
): number {
  return filterAttentionSignals(items, workspaceId).length;
}

function shouldUseInboxSignalSnapshot(
  inboxLoadState: 'idle' | 'loading' | 'loaded' | 'error',
  inboxItems: OperatorSignalCountItem[],
): boolean {
  if (inboxLoadState === 'loaded') {
    return true;
  }
  // Keep the last inbox snapshot during background reloads so counts/lists
  // do not thrash to unscoped runtime open_count and back.
  return inboxLoadState === 'loading' && inboxItems.length > 0;
}

export function resolveOperatorSignalCount(input: {
  inboxItems: OperatorSignalCountItem[];
  inboxLoadState: 'idle' | 'loading' | 'loaded' | 'error';
  runtimeSummaryOpenCount?: number | null;
  workspaceId?: string | null;
}): number {
  if (shouldUseInboxSignalSnapshot(input.inboxLoadState, input.inboxItems)) {
    return countActionableOpenSignals(input.inboxItems, input.workspaceId);
  }

  return Math.max(0, input.runtimeSummaryOpenCount ?? 0);
}

export function resolveAttentionSignalCount(input: {
  inboxItems: OperatorSignalCountItem[];
  inboxLoadState: 'idle' | 'loading' | 'loaded' | 'error';
  runtimeSummaryOpenCount?: number | null;
  workspaceId?: string | null;
  briefingTopSignals?: OperatorSignalCountItem[] | null;
}): number {
  if (shouldUseInboxSignalSnapshot(input.inboxLoadState, input.inboxItems)) {
    return countAttentionSignals(input.inboxItems, input.workspaceId);
  }

  const briefingSignals = input.briefingTopSignals ?? [];
  if (briefingSignals.length > 0) {
    return countAttentionSignals(briefingSignals, input.workspaceId);
  }

  return Math.max(0, input.runtimeSummaryOpenCount ?? 0);
}
