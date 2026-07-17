import { describe, expect, it } from 'vitest';

import {
  clearIdeRunRecovery,
  decideIdeRunRecovery,
  MAX_IDE_RUN_RECOVERY_ATTEMPTS,
  persistIdeRunRecovery,
  readIdeRunRecovery,
  waitForStableControlPlaneBootId,
  type IdeRunRecoveryRecord,
} from './ide-run-recovery';

function memoryStorage(): Pick<Storage, 'getItem' | 'setItem' | 'removeItem'> {
  const values = new Map<string, string>();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
}

function baseRecovery(
  overrides: Partial<IdeRunRecoveryRecord> = {},
): IdeRunRecoveryRecord {
  return {
    workspaceId: 'workspace_axon_watch',
    threadId: 'thread_agent',
    runId: 'run_interrupted',
    mode: 'agent',
    controlPlaneBootId: 'boot-before-restart',
    recoveryCount: 0,
    ...overrides,
  };
}

describe('IDE run recovery record', () => {
  it('persists an interrupted Debug run until that run completes', () => {
    const storage = memoryStorage();
    const record = baseRecovery({
      workspaceId: 'workspace_axon_local',
      threadId: 'thread_debug',
      runId: 'run_debug',
      mode: 'debug',
    });
    persistIdeRunRecovery(record, storage);
    expect(readIdeRunRecovery(storage)).toEqual(record);

    clearIdeRunRecovery('another_run', storage);
    expect(readIdeRunRecovery(storage)).toEqual(record);
    clearIdeRunRecovery('run_debug', storage);
    expect(readIdeRunRecovery(storage)).toBeNull();
  });

  it('persists linked Plan runs', () => {
    const storage = memoryStorage();
    const record = baseRecovery({
      threadId: 'thread_plan',
      runId: 'run_plan',
      mode: 'plan',
    });
    persistIdeRunRecovery(record, storage);
    expect(readIdeRunRecovery(storage)).toEqual(record);
  });
});

describe('decideIdeRunRecovery', () => {
  it('continues a failed orphaned run after boot id changes', () => {
    const decision = decideIdeRunRecovery({
      recovery: baseRecovery(),
      currentBootId: 'boot-after-restart',
      runPhase: 'failed',
      streamActive: false,
      mutationBusy: false,
      currentWorkspaceId: 'workspace_axon_watch',
    });
    expect(decision).toEqual({
      action: 'continue',
      linkExistingRun: false,
      nextRecoveryCount: 1,
    });
  });

  it('links an still-executing run after boot id changes', () => {
    const decision = decideIdeRunRecovery({
      recovery: baseRecovery(),
      currentBootId: 'boot-after-restart',
      runPhase: 'executing',
      streamActive: false,
      mutationBusy: false,
      currentWorkspaceId: 'workspace_axon_watch',
    });
    expect(decision).toEqual({
      action: 'continue',
      linkExistingRun: true,
      nextRecoveryCount: 1,
    });
  });

  it('reattaches a live Plan run after a same-boot refresh', () => {
    const decision = decideIdeRunRecovery({
      recovery: baseRecovery({ mode: 'plan' }),
      currentBootId: 'boot-before-restart',
      runPhase: 'executing',
      streamActive: false,
      mutationBusy: false,
      currentWorkspaceId: 'workspace_axon_watch',
    });
    expect(decision).toEqual({ action: 'reattach' });
  });

  it('clears a terminal run after a same-boot refresh', () => {
    const decision = decideIdeRunRecovery({
      recovery: baseRecovery(),
      currentBootId: 'boot-before-restart',
      runPhase: 'failed',
      streamActive: false,
      mutationBusy: false,
      currentWorkspaceId: 'workspace_axon_watch',
    });
    expect(decision).toEqual({ action: 'clear' });
  });

  it('stops after repeated restart recovery attempts', () => {
    const decision = decideIdeRunRecovery({
      recovery: baseRecovery({ recoveryCount: MAX_IDE_RUN_RECOVERY_ATTEMPTS }),
      currentBootId: 'boot-after-restart',
      runPhase: 'failed',
      streamActive: false,
      mutationBusy: false,
      currentWorkspaceId: 'workspace_axon_watch',
    });
    expect(decision.action).toBe('stop_retry');
  });

  it('clears recovery when the original run already completed', () => {
    const decision = decideIdeRunRecovery({
      recovery: baseRecovery(),
      currentBootId: 'boot-after-restart',
      runPhase: 'completed',
      streamActive: false,
      mutationBusy: false,
      currentWorkspaceId: 'workspace_axon_watch',
    });
    expect(decision).toEqual({ action: 'clear' });
  });
});

describe('waitForStableControlPlaneBootId', () => {
  it('returns null while the previous boot is still serving', async () => {
    const fetchImpl = (async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/api/readiness')) {
        return new Response(JSON.stringify({ status: 'ready' }), { status: 200 });
      }
      return new Response(
        JSON.stringify({ boot_id: 'boot-before-restart', status: 'ok' }),
        { status: 200 },
      );
    }) as typeof fetch;

    const bootId = await waitForStableControlPlaneBootId({
      previousBootId: 'boot-before-restart',
      stableMs: 50,
      timeoutMs: 120,
      fetchImpl,
      sleep: async () => undefined,
    });
    expect(bootId).toBeNull();
  });

  it('waits until the new boot id stays unchanged', async () => {
    let healthCalls = 0;
    const fetchImpl = (async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/api/readiness')) {
        return new Response(JSON.stringify({ status: 'ready' }), { status: 200 });
      }
      healthCalls += 1;
      const boot = healthCalls === 1 ? 'boot-bounce' : 'boot-stable';
      return new Response(JSON.stringify({ boot_id: boot, status: 'ok' }), {
        status: 200,
      });
    }) as typeof fetch;

    let now = 1_000;
    const realDateNow = Date.now;
    Date.now = () => now;
    try {
      const bootId = await waitForStableControlPlaneBootId({
        previousBootId: 'boot-before-restart',
        stableMs: 100,
        timeoutMs: 5_000,
        fetchImpl,
        sleep: async () => {
          now += 60;
        },
      });
      expect(bootId).toBe('boot-stable');
      expect(healthCalls).toBeGreaterThan(2);
    } finally {
      Date.now = realDateNow;
    }
  });
});
