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
  it('restores the selected mode independently for each workspace', () => {
    const storage = memoryStorage();
    persistWorkspaceComposerMode('workspace_debug', 'debug', storage);
    persistWorkspaceComposerMode('workspace_agent', 'agent', storage);

    expect(readWorkspaceComposerMode('workspace_debug', storage)).toBe('debug');
    expect(readWorkspaceComposerMode('workspace_agent', storage)).toBe('agent');
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

  it('migrates legacy workspace mode into the first thread that reads it', () => {
    const storage = memoryStorage();
    persistWorkspaceComposerMode('workspace_a', 'plan', storage);

    expect(readWorkspaceComposerMode('workspace_a', storage, 'thread_1')).toBe('plan');
    expect(readWorkspaceComposerMode('workspace_a', storage, 'thread_2')).toBeNull();
    expect(readWorkspaceComposerMode('workspace_a', storage)).toBeNull();
  });
});
