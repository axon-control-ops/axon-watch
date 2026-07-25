import type { BriefingAction, OperatorBriefing } from '../contracts/canonical';

import { canHandoffSignalToIde } from './signal-handoff-view';

export type BriefingActionShell = {
  handoffSignalToIde: (
    signal: {
      signal_id: string;
      workspace_id?: string | null;
      title: string;
      summary?: string | null;
      meta?: Record<string, unknown> | null;
    },
    options?: { autoSubmit?: boolean },
  ) => Promise<void>;
  focusMissionControl: () => void;
  focusCommandSeam: () => void;
  focusAttentionSidebar: (signalId?: string | null) => void;
};

export type BriefingActionResult =
  | { ok: true; kind: BriefingAction['kind'] }
  | { ok: false; reason: 'missing_signal_id' | 'unsupported_kind' };

export function findBriefingSignal(
  briefing: OperatorBriefing | null | undefined,
  signalId: string | null | undefined,
) {
  const id = String(signalId ?? '').trim();
  if (!id || !briefing) {
    return null;
  }
  return briefing.top_signals.find((signal) => signal.signal_id === id) ?? null;
}

export function briefingActionCtaLabel(action: BriefingAction): string {
  if (action.kind === 'review_signal') {
    return 'Hand off to IDE';
  }
  if (action.kind === 'approve_run' || action.kind === 'resume_run') {
    return 'Open Mission Control';
  }
  if (action.kind === 'inspect_runtime') {
    return 'Open command seam';
  }
  return action.title;
}

export async function executeBriefingAction(
  shell: BriefingActionShell,
  briefing: OperatorBriefing | null | undefined,
  action: BriefingAction,
): Promise<BriefingActionResult> {
  if (action.kind === 'approve_run' || action.kind === 'resume_run') {
    shell.focusMissionControl();
    return { ok: true, kind: action.kind };
  }

  if (action.kind === 'inspect_runtime') {
    shell.focusCommandSeam();
    return { ok: true, kind: action.kind };
  }

  if (action.kind === 'review_signal') {
    const signalId = String(action.signal_id ?? '').trim();
    if (!signalId) {
      shell.focusAttentionSidebar(null);
      return { ok: false, reason: 'missing_signal_id' };
    }

    const signal = findBriefingSignal(briefing, signalId);
    const handoffInput = {
      signal_id: signalId,
      workspace_id: action.workspace_id ?? signal?.workspace_id ?? null,
      title: signal?.title?.trim() || action.title,
      summary: signal?.summary?.trim() || action.detail,
      meta: signal?.meta ?? null,
    };

    if (canHandoffSignalToIde(handoffInput)) {
      await shell.handoffSignalToIde(handoffInput, { autoSubmit: false });
      return { ok: true, kind: action.kind };
    }

    shell.focusAttentionSidebar(signalId);
    return { ok: true, kind: action.kind };
  }

  return { ok: false, reason: 'unsupported_kind' };
}
