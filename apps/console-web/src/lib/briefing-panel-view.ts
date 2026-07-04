import type { OperatorBriefing } from '../contracts/canonical';

export type BriefingPanelLoadState = 'idle' | 'loading' | 'loaded' | 'error';

export function briefingPanelHeadline(
  briefing: OperatorBriefing | null,
  loadState: BriefingPanelLoadState,
): string {
  if (loadState === 'loading') {
    return 'Loading OperatorBriefing';
  }

  if (loadState === 'error') {
    return 'OperatorBriefing unavailable';
  }

  if (!briefing) {
    return 'Awaiting OperatorBriefing';
  }

  if (briefing.pending_approvals.count === 0) {
    return 'No pending approvals';
  }

  return `${briefing.pending_approvals.count} pending approval(s)`;
}

export function briefingHasActions(briefing: OperatorBriefing | null): boolean {
  return Boolean(briefing && briefing.next_safe_actions.length > 0);
}

export function briefingIsEmpty(briefing: OperatorBriefing | null): boolean {
  if (!briefing) {
    return true;
  }

  return briefing.pending_approvals.count === 0 && briefing.next_safe_actions.length === 0;
}
