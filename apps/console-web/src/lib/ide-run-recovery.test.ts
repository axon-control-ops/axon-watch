import { describe, expect, it } from 'vitest';

import {
  clearIdeRunRecovery,
  persistIdeRunRecovery,
  readIdeRunRecovery,
} from './ide-run-recovery';

function memoryStorage(): Pick<Storage, 'getItem' | 'setItem' | 'removeItem'> {
  const values = new Map<string, string>();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
}

describe('IDE run recovery record', () => {
  it('persists an interrupted Debug run until that run completes', () => {
    const storage = memoryStorage();
    const record = {
      workspaceId: 'workspace_axon_local',
      threadId: 'thread_debug',
      runId: 'run_debug',
      mode: 'debug' as const,
      controlPlaneBootId: 'boot-before-restart',
      recoveryCount: 0,
    };
    persistIdeRunRecovery(record, storage);
    expect(readIdeRunRecovery(storage)).toEqual(record);

    clearIdeRunRecovery('another_run', storage);
    expect(readIdeRunRecovery(storage)).toEqual(record);
    clearIdeRunRecovery('run_debug', storage);
    expect(readIdeRunRecovery(storage)).toBeNull();
  });
});
