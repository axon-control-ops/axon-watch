import { triggerAutonomyScan } from '../api/autonomy-api';
import { parseChatUiAction } from './chat-ui-action';

const triggeredAdviseKeys = new Set<string>();

export function maybeTriggerAutoAttendAdvise(input: {
  adviseUiAction: unknown;
  autonomyMode: string | null | undefined;
}): boolean {
  if (String(input.autonomyMode ?? '').trim().toLowerCase() !== 'full') {
    return false;
  }
  const action = parseChatUiAction(input.adviseUiAction);
  if (action?.type !== 'switch_workspace' || action.auto_attend !== true) {
    return false;
  }
  const key = `${action.workspace_id}:${action.signal_id ?? 'handoff'}`;
  if (triggeredAdviseKeys.has(key)) {
    return false;
  }
  triggeredAdviseKeys.add(key);
  void triggerAutonomyScan().catch(() => {
    triggeredAdviseKeys.delete(key);
  });
  return true;
}

export function resetAutoAttendAdviseDedupeForTests(): void {
  triggeredAdviseKeys.clear();
}
