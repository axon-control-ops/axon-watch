import type {
  BriefingAction,
  OperatorBriefing,
  RunRecord,
  RuntimeSummaryActiveRun,
} from '../contracts/canonical';

import { formatRunDisplayName } from './run-display';
import { runPhaseTag } from './mockup-shell-view';

export type OpenLoopFocusKind = 'attention' | 'mission' | 'command';

export type OpenLoopRow = {
  id: string;
  label: string;
  meta?: string;
  focusKind: OpenLoopFocusKind;
  signalId?: string | null;
};

export type BuildBriefingOpenLoopOptions = {
  compact?: boolean;
  primaryActiveRun?: Pick<
    RunRecord,
    'run_id' | 'summary' | 'detail' | 'phase' | 'workspace_id'
  > | null;
  fleetActiveRuns?: Array<
    Pick<RuntimeSummaryActiveRun, 'run_id' | 'workspace_id' | 'phase' | 'title'>
  >;
  workspaceId?: string | null;
};

const MAX_ACTIONS = 2;
/** Cap ~4 lines: top signal + receipt meta + up to 2 actions. */
const MAX_ROWS = 4;
/** Galaxy-compact hero: keep the dock useful without overflowing. */
const MAX_GALAXY_ROWS = 2;

const LIVE_RUN_PHASES = new Set(['executing', 'review_ready', 'awaiting_approval', 'paused']);

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

function isLiveRunPhase(phase: string | null | undefined): boolean {
  return Boolean(phase && LIVE_RUN_PHASES.has(phase));
}

export function buildBriefingOpenLoopRows(
  briefing: OperatorBriefing | null | undefined,
  options?: BuildBriefingOpenLoopOptions,
): OpenLoopRow[] {
  const maxRows = options?.compact ? MAX_GALAXY_ROWS : MAX_ROWS;
  const maxActions = options?.compact ? 1 : MAX_ACTIONS;
  const rows: OpenLoopRow[] = [];
  const primary = options?.primaryActiveRun;
  const primaryLive = primary && isLiveRunPhase(primary.phase) ? primary : null;

  if (briefing) {
    const dueReminder = briefing.due_reminders?.[0] ?? briefing.memory_highlights?.find(
      (item) => item.kind === 'reminder' || Boolean(item.due_at),
    );
    if (dueReminder) {
      rows.push({
        id: `reminder:${dueReminder.memory_id}`,
        label: dueReminder.title,
        meta: dueReminder.why_now || dueReminder.due_at || 'Due reminder',
        focusKind: 'attention',
        signalId: null,
      });
    }

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
  }

  if (primaryLive && rows.length < maxRows) {
    rows.push({
      id: `run:${primaryLive.run_id}`,
      label: formatRunDisplayName(primaryLive),
      meta: runPhaseTag(primaryLive.phase),
      focusKind: 'mission',
      signalId: null,
    });
  }

  if (!primaryLive && rows.length < maxRows) {
    const workspaceId = options?.workspaceId?.trim() || null;
    const elsewhere = (options?.fleetActiveRuns ?? []).filter(
      (run) =>
        isLiveRunPhase(run.phase) && (!workspaceId || run.workspace_id !== workspaceId),
    );
    if (elsewhere.length > 0) {
      const noun = elsewhere.length === 1 ? 'run' : 'runs';
      rows.push({
        id: `fleet-runs:${elsewhere.length}`,
        label: `${elsewhere.length} ${noun} in flight (other workspaces)`,
        meta: 'Open Brain view',
        focusKind: 'mission',
        signalId: null,
      });
    }
  }

  if (briefing) {
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
  }

  return rows.slice(0, maxRows);
}

export function briefingHasOpenLoops(
  briefing: OperatorBriefing | null | undefined,
  options?: BuildBriefingOpenLoopOptions,
): boolean {
  return buildBriefingOpenLoopRows(briefing, options).length > 0;
}
