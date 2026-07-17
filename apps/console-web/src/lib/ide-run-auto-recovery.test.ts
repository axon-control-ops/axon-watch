import { describe, expect, it, vi } from 'vitest';

import { executeIdeRunRecovery } from './ide-run-auto-recovery';
import type { IdeRunRecoveryRecord } from './ide-run-recovery';

const recovery: IdeRunRecoveryRecord = {
  workspaceId: 'workspace_alpha',
  threadId: 'thread_plan',
  runId: 'run_plan',
  mode: 'plan',
  controlPlaneBootId: 'boot_original',
  recoveryCount: 0,
};

function callbacks() {
  return {
    streamActive: () => false,
    mutationBusy: () => false,
    currentWorkspaceId: () => 'workspace_alpha',
    linkRun: vi.fn(),
    reattach: vi.fn(async () => undefined),
    reportError: vi.fn(),
    dispatchContinuation: vi.fn(async () => true),
    clearRecovery: vi.fn(),
    persistRecovery: vi.fn(),
  };
}

describe('executeIdeRunRecovery', () => {
  it('reattaches a live Plan stream after browser refresh', async () => {
    const handlers = callbacks();
    await executeIdeRunRecovery({
      recovery,
      loadRunPhase: async () => 'executing',
      waitForBootId: async () => null,
      fetchBootId: async () => 'boot_original',
      ...handlers,
    });

    expect(handlers.reattach).toHaveBeenCalledWith(recovery);
    expect(handlers.dispatchContinuation).not.toHaveBeenCalled();
    expect(handlers.clearRecovery).not.toHaveBeenCalled();
  });

  it('continues a Plan run after control-plane restart', async () => {
    const handlers = callbacks();
    await executeIdeRunRecovery({
      recovery,
      loadRunPhase: async () => 'failed',
      waitForBootId: async () => 'boot_restarted',
      fetchBootId: async () => 'boot_restarted',
      ...handlers,
    });

    expect(handlers.clearRecovery).toHaveBeenCalledWith('run_plan');
    expect(handlers.dispatchContinuation).toHaveBeenCalledWith(
      expect.objectContaining({
        mode: 'plan',
        threadId: 'thread_plan',
        linkedRunId: null,
        recoveryCount: 1,
      }),
    );
    expect(handlers.reattach).not.toHaveBeenCalled();
  });
});
