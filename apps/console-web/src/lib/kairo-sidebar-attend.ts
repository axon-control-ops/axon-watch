/** Attend CTA helpers for VAXON Advise one-click switch + Attention. */

import {
  applyChatUiAction,
  parseChatUiAction,
  type ChatUiAction,
  type WorkspaceSwitchShell,
} from './chat-ui-action';
import { isAffirmativeOperatorReply } from './vaxon-reply-prompt';

export function parseAdviseUiAction(value: unknown): ChatUiAction | null {
  return parseChatUiAction(value);
}

export function adviseAttendCtaLabel(action: ChatUiAction | null): string | null {
  if (!action) {
    return null;
  }
  if (action.type === 'switch_workspace' && action.cta_label) {
    return action.cta_label;
  }
  return 'Attend';
}

export function applyAdviseAttendAction(
  shell: WorkspaceSwitchShell,
  action: ChatUiAction | null,
): void {
  if (!action) {
    shell.focusAttentionSidebar?.();
    return;
  }
  applyChatUiAction(shell, action);
}

/** Affirmative speech reply should execute Attend when briefing has a ui_action. */
export function shouldApplyAdviseAttendOnAffirm(input: {
  message: string;
  adviseUiAction: ChatUiAction | null;
}): boolean {
  return Boolean(input.adviseUiAction) && isAffirmativeOperatorReply(input.message);
}

/** Apply an affirmative Attend reply and mark the turn as fully consumed. */
export function consumeAdviseAttendReply(
  shell: WorkspaceSwitchShell,
  input: {
    message: string;
    adviseUiAction: ChatUiAction | null;
  },
): boolean {
  if (!shouldApplyAdviseAttendOnAffirm(input)) {
    return false;
  }
  applyAdviseAttendAction(shell, input.adviseUiAction);
  return true;
}
