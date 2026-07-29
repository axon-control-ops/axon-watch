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
  startCloudflareTunnel?: () => Promise<void>;
  loadRuntimeSummary?: (opts?: { background?: boolean }) => Promise<void>;
  loadOperatorBriefing?: () => Promise<void>;
  loadInbox?: () => Promise<void>;
};

function openVault(shell: ReportTheaterActionShell): void {
  if (typeof shell.openVaultSurface === 'function') {
    shell.openVaultSurface();
    return;
  }
  navigateToAppSurface('vault');
}

async function restartPublicTunnel(shell: ReportTheaterActionShell): Promise<void> {
  if (typeof shell.startCloudflareTunnel === 'function') {
    await shell.startCloudflareTunnel();
  }
  await Promise.all([
    shell.loadRuntimeSummary?.({ background: true }),
    shell.loadOperatorBriefing?.(),
    shell.loadInbox?.(),
  ]);
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
    if (
      action.action_id === 'theater_start_tunnel' ||
      /tunnel/i.test(action.title || '')
    ) {
      await restartPublicTunnel(shell);
      return { ok: true, kind: action.kind };
    }
    const preferVault =
      action.action_id === 'theater_open_vault' ||
      /^open vault$/i.test(action.title) ||
      /vault/i.test(action.detail || '');
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
    if (!signalId) {
      // Workspace switch still counts — Attention opens even without a concrete signal id.
      return { ok: true, kind: action.kind };
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
    return { ok: true, kind: action.kind };
  }
  return executeBriefingAction(shell, briefing, action);
}
