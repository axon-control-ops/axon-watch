import type { BriefingAction, OperatorBriefing } from '../../contracts/canonical';
import {
  executeBriefingAction,
  type BriefingActionResult,
  type BriefingActionShell,
} from '../../lib/briefing-action-executor';

export type ReportTheaterActionShell = BriefingActionShell & {
  focusMissionControl: () => void;
  setLeftSidebarMode?: (mode: 'attention') => void;
  layoutMode?: string;
};

/**
 * Theater initiative stays on Mission Control — open Attention, do not dump into IDE.
 */
export async function executeReportTheaterAction(
  shell: ReportTheaterActionShell,
  briefing: OperatorBriefing | null | undefined,
  action: BriefingAction,
): Promise<BriefingActionResult> {
  if (action.kind === 'review_signal') {
    shell.focusMissionControl();
    const signalId = String(action.signal_id ?? '').trim() || null;
    shell.focusAttentionSidebar(signalId);
    shell.setLeftSidebarMode?.('attention');
    return { ok: true, kind: action.kind };
  }
  return executeBriefingAction(shell, briefing, action);
}
