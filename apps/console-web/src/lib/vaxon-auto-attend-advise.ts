/** Full-autonomy attend for cross-workspace Advise — no operator hunt/switch. */

import { triggerAutonomyScan } from '../api/autonomy-api';
import type { ChatUiAction } from './chat-ui-action';

const recentlyTriggeredKeys = new Set<string>();

export function adviseAutoAttendKey(action: ChatUiAction | null | undefined): string | null {
  if (!action || action.type !== 'switch_workspace' || !action.auto_attend) {
    return null;
  }
  const workspaceId = String(action.workspace_id || '').trim();
  if (!workspaceId) {
    return null;
  }
  const signalId = String(action.signal_id || '').trim();
  return `${workspaceId}:${signalId || 'attention'}`;
}

export function shouldAutoAttendAdvise(input: {
  autonomyMode: string | null | undefined;
  adviseUiAction: ChatUiAction | null | undefined;
}): boolean {
  const mode = String(input.autonomyMode || '')
    .trim()
    .toLowerCase();
  if (mode !== 'full') {
    return false;
  }
  return Boolean(adviseAutoAttendKey(input.adviseUiAction));
}

/** Fire a bounded attend scan once per advise key (does not yank the IDE focus). */
export async function maybeTriggerAutoAttendAdvise(input: {
  autonomyMode: string | null | undefined;
  adviseUiAction: ChatUiAction | null | undefined;
}): Promise<boolean> {
  if (!shouldAutoAttendAdvise(input)) {
    return false;
  }
  const key = adviseAutoAttendKey(input.adviseUiAction);
  if (!key || recentlyTriggeredKeys.has(key)) {
    return false;
  }
  recentlyTriggeredKeys.add(key);
  try {
    await triggerAutonomyScan();
    return true;
  } catch {
    // Allow a later briefing tick to retry if the scan endpoint rejected.
    recentlyTriggeredKeys.delete(key);
    return false;
  }
}

/** Test helper — clears dedupe memory between cases. */
export function resetAutoAttendAdviseMemoryForTests(): void {
  recentlyTriggeredKeys.clear();
}
