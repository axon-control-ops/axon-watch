import type { BriefingAction, OperatorBriefing } from '../../contracts/canonical';
import {
  executeBriefingAction,
  findBriefingSignal,
  type BriefingActionResult,
  type BriefingActionShell,
} from '../../lib/briefing-action-executor';
import { navigateToAppSurface } from '../../lib/app-surface-route';

export type ReportTheaterActionShell = BriefingActionShell & {
  focusMissionControl: () => void;
  setLeftSidebarMode?: (mode: 'attention') => void;
  setCurrentWorkspace?: (workspaceId: string) => void;
  layoutMode?: string;
  openVaultSurface?: () => void;
};

function openVault(shell: ReportTheaterActionShell): void {
  if (typeof shell.openVaultSurface === 'function') {
    shell.openVaultSurface();
    return;
  }
  navigateToAppSurface('vault');
}

/**
 * Theater initiative stays on Mission Control — open Attention, do not dump into IDE.
 * When runtime/vault is the recovery action, open Vault instead of a doomed investigation.
 */
export async function executeReportTheaterAction(
  shell: ReportTheaterActionShell,
  briefing: OperatorBriefing | null | undefined,
  action: BriefingAction,
): Promise<BriefingActionResult> {
  if (action.kind === 'inspect_runtime') {
    const preferVault =
      action.action_id === 'theater_open_vault' ||
      /^open vault$/i.test(action.title) ||
      /vault/i.test(action.detail || '');
    // #region agent log
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'readiness-recovery-fix',hypothesisId:'H51',location:'report-theater-execute.ts:inspect-runtime',message:'executing runtime recovery directive',data:{preferVault,actionId:action.action_id,title:action.title},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    if (preferVault) {
      openVault(shell);
      return { ok: true, kind: action.kind };
    }
    return executeBriefingAction(shell, briefing, action);
  }

  if (action.kind === 'review_signal') {
    const workspaceId = String(action.workspace_id ?? '').trim();
    const signalId = String(action.signal_id ?? '').trim() || null;
    const signal = findBriefingSignal(briefing, signalId);
    if (workspaceId) {
      shell.setCurrentWorkspace?.(workspaceId);
    }
    shell.focusMissionControl();
    shell.focusAttentionSidebar(signalId);
    shell.setLeftSidebarMode?.('attention');
    // #region agent log
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'workspace-switch-fix',hypothesisId:'H38,H39',location:'report-theater-execute.ts:review-signal',message:'executed report workspace and Attention switch',data:{workspaceId,signalId,layoutMode:shell.layoutMode??null},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    if (!signalId) {
      return { ok: false, reason: 'missing_signal_id' };
    }
    await shell.handoffSignalToIde(
      {
        signal_id: signalId,
        workspace_id: workspaceId || signal?.workspace_id || null,
        title: signal?.title?.trim() || action.title,
        summary: signal?.summary?.trim() || action.detail,
        meta: signal?.meta ?? null,
      },
      { autoSubmit: true },
    );
    // #region agent log
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'report-auto-start-fix',hypothesisId:'H43,H44,H45',location:'report-theater-execute.ts:auto-start',message:'switched to promised workspace and submitted investigation',data:{workspaceId,signalId,autoSubmit:true,layoutMode:shell.layoutMode??null},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    return { ok: true, kind: action.kind };
  }
  return executeBriefingAction(shell, briefing, action);
}
