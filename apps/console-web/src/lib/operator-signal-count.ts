import { isBootstrapSummarySignal } from './operator-signal-hints';

export type OperatorSignalCountItem = {
  signal_id: string;
  title: string;
  status?: string | null;
  workspace_id?: string | null;
  severity?: string | null;
  summary?: string | null;
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

export function resolveOperatorSignalCount(input: {
  inboxItems: OperatorSignalCountItem[];
  inboxLoadState: 'idle' | 'loading' | 'loaded' | 'error';
  runtimeSummaryOpenCount?: number | null;
  workspaceId?: string | null;
}): number {
  if (input.inboxLoadState === 'loaded') {
    return countActionableOpenSignals(input.inboxItems, input.workspaceId);
  }

  return Math.max(0, input.runtimeSummaryOpenCount ?? 0);
}
