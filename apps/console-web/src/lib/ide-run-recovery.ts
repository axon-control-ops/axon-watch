import { apiUrl } from '../api/client';

export type IdeRunRecoveryRecord = {
  workspaceId: string;
  threadId: string;
  runId: string;
  mode: 'agent' | 'debug';
  controlPlaneBootId: string;
  recoveryCount: number;
};

export type IdeRunRecoveryDecision =
  | { action: 'skip' }
  | { action: 'clear' }
  | { action: 'stop_retry'; reason: string }
  | {
      action: 'continue';
      /** Link to the recovered run when it is still executing; otherwise start a fresh run. */
      linkExistingRun: boolean;
      nextRecoveryCount: number;
    };

const RECOVERY_KEY = 'axon-x:ide-run-recovery:v1';
/** Allow one retry when the continuation itself is killed by the same restart wave. */
export const MAX_IDE_RUN_RECOVERY_ATTEMPTS = 2;
export const SERVER_RESTART_CONTINUATION_PROMPT =
  'Continue the interrupted run from after the server restart. Do not repeat any restart or shutdown command that already completed. First verify current service health, then continue from the next unfinished step in the existing thread.';

/** How long boot_id must stay unchanged before auto-continue is safe. */
export const CONTROL_PLANE_BOOT_STABLE_MS = 2_500;
/** Give reload / restart bounce time to settle before giving up. */
export const CONTROL_PLANE_BOOT_STABLE_TIMEOUT_MS = 45_000;

type RecoveryFetch = typeof fetch;

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

export async function fetchControlPlaneBootId(
  fetchImpl: RecoveryFetch = fetch,
): Promise<string> {
  const response = await fetchImpl(apiUrl('/api/health'));
  if (!response.ok) {
    throw new Error(`control-plane health failed with status ${response.status}`);
  }
  const payload = (await response.json()) as { boot_id?: unknown };
  return String(payload.boot_id ?? '').trim();
}

export async function fetchControlPlaneReady(
  fetchImpl: RecoveryFetch = fetch,
): Promise<boolean> {
  try {
    const response = await fetchImpl(apiUrl('/api/readiness'));
    if (!response.ok) {
      return false;
    }
    const payload = (await response.json()) as { status?: unknown };
    return String(payload.status ?? '').trim().toLowerCase() === 'ready';
  } catch {
    return false;
  }
}

/**
 * Wait until readiness succeeds with the same boot_id across a short window.
 * Prevents auto-continue from racing a reload or second restart bounce.
 * Returns null immediately when the previous boot is still healthy (no restart yet).
 */
export async function waitForStableControlPlaneBootId(options?: {
  previousBootId?: string;
  stableMs?: number;
  timeoutMs?: number;
  fetchImpl?: RecoveryFetch;
  sleep?: (ms: number) => Promise<void>;
}): Promise<string | null> {
  const previousBootId = (options?.previousBootId ?? '').trim();
  const stableMs = options?.stableMs ?? CONTROL_PLANE_BOOT_STABLE_MS;
  const timeoutMs = options?.timeoutMs ?? CONTROL_PLANE_BOOT_STABLE_TIMEOUT_MS;
  const fetchImpl = options?.fetchImpl ?? fetch;
  const sleep = options?.sleep ?? delay;
  const deadline = Date.now() + timeoutMs;

  let candidate = '';
  let candidateSince = 0;

  while (Date.now() < deadline) {
    try {
      const ready = await fetchControlPlaneReady(fetchImpl);
      const bootId = ready ? await fetchControlPlaneBootId(fetchImpl) : '';
      if (!ready || !bootId) {
        candidate = '';
        candidateSince = 0;
      } else if (previousBootId && bootId === previousBootId) {
        // Same process as before the marker was written — no restart to recover from.
        return null;
      } else if (bootId !== candidate) {
        candidate = bootId;
        candidateSince = Date.now();
      } else if (Date.now() - candidateSince >= stableMs) {
        return candidate;
      }
    } catch {
      candidate = '';
      candidateSince = 0;
    }
    await sleep(Math.min(750, Math.max(200, Math.floor(stableMs / 3))));
  }

  return null;
}

/**
 * Decide whether an IDE agent/debug run should auto-continue after a control-plane restart.
 * Recovery markers survive in sessionStorage; orphaned runs are usually marked failed on boot.
 */
export function decideIdeRunRecovery(input: {
  recovery: IdeRunRecoveryRecord | null;
  currentBootId: string;
  runPhase: string | null | undefined;
  streamActive: boolean;
  mutationBusy: boolean;
  currentWorkspaceId: string | null | undefined;
}): IdeRunRecoveryDecision {
  const recovery = input.recovery;
  if (!recovery) {
    return { action: 'skip' };
  }
  if (input.streamActive || input.mutationBusy) {
    return { action: 'skip' };
  }
  if (input.currentWorkspaceId !== recovery.workspaceId) {
    return { action: 'skip' };
  }
  if (!input.currentBootId || input.currentBootId === recovery.controlPlaneBootId) {
    return { action: 'skip' };
  }
  if (!input.runPhase) {
    return { action: 'clear' };
  }
  if (recovery.recoveryCount >= MAX_IDE_RUN_RECOVERY_ATTEMPTS) {
    return {
      action: 'stop_retry',
      reason:
        'Automatic continuation stopped after repeated server restarts. Review the run before continuing manually.',
    };
  }

  if (input.runPhase === 'executing') {
    return {
      action: 'continue',
      linkExistingRun: true,
      nextRecoveryCount: recovery.recoveryCount + 1,
    };
  }

  // Startup reconcile marks orphaned executes as failed/cancelled — still continue.
  if (input.runPhase === 'failed' || input.runPhase === 'cancelled') {
    return {
      action: 'continue',
      linkExistingRun: false,
      nextRecoveryCount: recovery.recoveryCount + 1,
    };
  }

  if (input.runPhase === 'completed' || input.runPhase === 'review_ready') {
    return { action: 'clear' };
  }

  return { action: 'skip' };
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
