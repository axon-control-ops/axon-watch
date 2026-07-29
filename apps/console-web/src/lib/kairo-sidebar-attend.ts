/** Attend CTA helpers for VAXON Advise one-click switch + Attention. */

import {
  applyChatUiAction,
  parseChatUiAction,
  type ChatUiAction,
  type WorkspaceSwitchShell,
} from './chat-ui-action';

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
