import type { BriefingAction, OperatorBriefing } from '../contracts/canonical';

export type OpenLoopFocusKind = 'attention' | 'mission' | 'command';

export type OpenLoopRow = {
  id: string;
  label: string;
  meta?: string;
  focusKind: OpenLoopFocusKind;
  signalId?: string | null;
};

const MAX_ACTIONS = 2;
/** Cap ~4 lines: top signal + receipt meta + up to 2 actions. */
const MAX_ROWS = 4;
/** Galaxy-compact hero: keep the dock useful without overflowing. */
const MAX_GALAXY_ROWS = 2;

function deliveryBadge(signal: OperatorBriefing['top_signals'][number]): string | undefined {
  const receipt = signal.latest_receipt_id?.trim();
  if (receipt) {
    return `Receipt ${receipt}`;
  }

  const delivery = signal.delivery_state?.trim();
  if (!delivery || delivery === 'not_required' || delivery === 'pending') {
    return undefined;
  }

  return `Delivery ${delivery}`;
}

function focusKindForAction(action: BriefingAction): OpenLoopFocusKind {
  if (action.kind === 'review_signal') {
    return 'attention';
  }
  if (action.kind === 'inspect_runtime') {
    return 'command';
  }
  return 'mission';
}

export function buildBriefingOpenLoopRows(
  briefing: OperatorBriefing | null | undefined,
  options?: { compact?: boolean },
): OpenLoopRow[] {
  if (!briefing) {
    return [];
  }

  const maxRows = options?.compact ? MAX_GALAXY_ROWS : MAX_ROWS;
  const maxActions = options?.compact ? 1 : MAX_ACTIONS;
  const rows: OpenLoopRow[] = [];
  const topSignal = briefing.top_signals[0];

  if (topSignal) {
    rows.push({
      id: `signal:${topSignal.signal_id}`,
      label: topSignal.title,
      meta: deliveryBadge(topSignal),
      focusKind: 'attention',
      signalId: topSignal.signal_id,
    });
  } else if (briefing.pending_approvals.count > 0) {
    const first = briefing.pending_approvals.items[0];
    rows.push({
      id: `approval:${first?.run_id ?? 'pending'}`,
      label:
        briefing.pending_approvals.count === 1
          ? '1 approval waiting'
          : `${briefing.pending_approvals.count} approvals waiting`,
      meta: first?.run_id ? `Run ${first.run_id}` : undefined,
      focusKind: 'mission',
      signalId: null,
    });
  }

  for (const action of briefing.next_safe_actions.slice(0, maxActions)) {
    if (rows.length >= maxRows) {
      break;
    }
    rows.push({
      id: `action:${action.action_id}`,
      label: action.title,
      meta: action.detail,
      focusKind: focusKindForAction(action),
      signalId: action.signal_id,
    });
  }

  return rows.slice(0, maxRows);
}

export function briefingHasOpenLoops(briefing: OperatorBriefing | null | undefined): boolean {
  return buildBriefingOpenLoopRows(briefing).length > 0;
}
