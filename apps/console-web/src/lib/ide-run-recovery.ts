import { apiUrl } from '../api/client';

export type IdeRunRecoveryRecord = {
  workspaceId: string;
  threadId: string;
  runId: string;
  mode: 'agent' | 'debug';
  controlPlaneBootId: string;
  recoveryCount: number;
};

const RECOVERY_KEY = 'axon-x:ide-run-recovery:v1';
export const SERVER_RESTART_CONTINUATION_PROMPT =
  'Continue the interrupted run from after the server restart. Do not repeat any restart or shutdown command that already completed. First verify current service health, then continue from the next unfinished step in the existing thread.';

export async function fetchControlPlaneBootId(): Promise<string> {
  const response = await fetch(apiUrl('/api/health'));
  if (!response.ok) {
    throw new Error(`control-plane health failed with status ${response.status}`);
  }
  const payload = (await response.json()) as { boot_id?: unknown };
  return String(payload.boot_id ?? '').trim();
}

export function persistIdeRunRecovery(
  record: IdeRunRecoveryRecord,
  storage: Pick<Storage, 'setItem'> = sessionStorage,
): void {
  storage.setItem(RECOVERY_KEY, JSON.stringify(record));
}

export function readIdeRunRecovery(
  storage: Pick<Storage, 'getItem'> = sessionStorage,
): IdeRunRecoveryRecord | null {
  try {
    const parsed = JSON.parse(storage.getItem(RECOVERY_KEY) ?? 'null') as Partial<IdeRunRecoveryRecord> | null;
    if (
      !parsed ||
      !parsed.workspaceId ||
      !parsed.threadId ||
      !parsed.runId ||
      !parsed.controlPlaneBootId ||
      (parsed.mode !== 'agent' && parsed.mode !== 'debug')
    ) {
      return null;
    }
    return {
      workspaceId: parsed.workspaceId,
      threadId: parsed.threadId,
      runId: parsed.runId,
      mode: parsed.mode,
      controlPlaneBootId: parsed.controlPlaneBootId,
      recoveryCount: Number.isFinite(parsed.recoveryCount)
        ? Math.max(0, Number(parsed.recoveryCount))
        : 0,
    };
  } catch {
    return null;
  }
}

export function clearIdeRunRecovery(
  runId?: string,
  storage: Pick<Storage, 'getItem' | 'removeItem'> = sessionStorage,
): void {
  const existing = readIdeRunRecovery(storage);
  if (!runId || existing?.runId === runId) {
    storage.removeItem(RECOVERY_KEY);
  }
}
