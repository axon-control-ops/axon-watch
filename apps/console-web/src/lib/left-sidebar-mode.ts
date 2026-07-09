import type { OperatorBriefing } from '../contracts/canonical';
import { briefingHasInterruptiveSignals } from './dock-seam-layout';
import {
  filterActionableOpenSignals,
  type OperatorSignalCountItem,
} from './operator-signal-count';

export type LeftSidebarMode = 'workspaces' | 'attention';

export const LEFT_SIDEBAR_MODE_KEY = 'axon-x-left-sidebar-mode';

export function resolveDefaultLeftSidebarMode(input: {
  pendingApprovals: number;
  briefing: OperatorBriefing | null;
}): LeftSidebarMode {
  if (input.pendingApprovals > 0) {
    return 'attention';
  }

  if (briefingHasInterruptiveSignals(input.briefing)) {
    return 'attention';
  }

  return 'workspaces';
}

export function leftSidebarAttentionBadgeCount(input: {
  pendingApprovals: number;
  briefing: OperatorBriefing | null;
  inboxItems?: OperatorSignalCountItem[];
  inboxLoadState?: 'idle' | 'loading' | 'loaded' | 'error';
}): number {
  let interruptiveSignals = 0;

  if (input.inboxLoadState === 'loaded' && input.inboxItems) {
    interruptiveSignals = filterActionableOpenSignals(input.inboxItems).filter((signal) => {
      const severity = (signal.severity ?? '').toLowerCase();
      return severity === 'high' || severity === 'critical';
    }).length;
  } else {
    interruptiveSignals =
      input.briefing?.top_signals.filter(
        (signal) => signal.severity === 'high' || signal.severity === 'critical',
      ).length ?? 0;
  }

  return input.pendingApprovals + interruptiveSignals;
}

export function leftSidebarModeLabel(mode: LeftSidebarMode): string {
  return mode === 'workspaces' ? 'Workspaces' : 'Attention';
}

export function readStoredLeftSidebarMode(): LeftSidebarMode | null {
  if (typeof sessionStorage === 'undefined') {
    return null;
  }

  const raw = sessionStorage.getItem(LEFT_SIDEBAR_MODE_KEY);
  return raw === 'workspaces' || raw === 'attention' ? raw : null;
}

export function persistLeftSidebarMode(mode: LeftSidebarMode): void {
  if (typeof sessionStorage === 'undefined') {
    return;
  }

  sessionStorage.setItem(LEFT_SIDEBAR_MODE_KEY, mode);
}
