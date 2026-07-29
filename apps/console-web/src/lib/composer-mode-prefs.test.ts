import { describe, expect, it } from 'vitest';

import {
  persistWorkspaceComposerMode,
  readWorkspaceComposerMode,
} from './composer-mode-prefs';

function memoryStorage(): Pick<Storage, 'getItem' | 'setItem'> {
  const values = new Map<string, string>();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  };
}

describe('workspace composer mode preferences', () => {
  it('does not persist or restore mode without a thread id', () => {
    const storage = memoryStorage();
    persistWorkspaceComposerMode('workspace_debug', 'debug', storage);
    persistWorkspaceComposerMode('workspace_agent', 'agent', storage);

    expect(readWorkspaceComposerMode('workspace_debug', storage)).toBeNull();
    expect(readWorkspaceComposerMode('workspace_agent', storage)).toBeNull();
    expect(readWorkspaceComposerMode('workspace_other', storage)).toBeNull();
  });

  it('isolates mode per conversation thread', () => {
    const storage = memoryStorage();
    persistWorkspaceComposerMode('workspace_a', 'plan', storage, 'thread_1');
    persistWorkspaceComposerMode('workspace_a', 'agent', storage, 'thread_2');

    expect(readWorkspaceComposerMode('workspace_a', storage, 'thread_1')).toBe('plan');
    expect(readWorkspaceComposerMode('workspace_a', storage, 'thread_2')).toBe('agent');
    expect(readWorkspaceComposerMode('workspace_a', storage, 'thread_3')).toBeNull();
  });

  it('does not migrate legacy workspace mode into the first thread that reads it', () => {
    const storage = memoryStorage();
    storage.setItem(
      'axon-x:ide-composer-mode-by-workspace:v2',
      JSON.stringify({ workspace_a: 'plan' }),
    );

    expect(readWorkspaceComposerMode('workspace_a', storage, 'thread_1')).toBeNull();
    expect(readWorkspaceComposerMode('workspace_a', storage, 'thread_2')).toBeNull();
    expect(readWorkspaceComposerMode('workspace_a', storage)).toBeNull();
  });
});
