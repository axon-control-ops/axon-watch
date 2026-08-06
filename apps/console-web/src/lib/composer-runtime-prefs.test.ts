import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  readComposerRuntimePrefs,
  writeComposerRuntimePrefs,
} from './composer-runtime-prefs';

function memoryStorage(): Pick<Storage, 'getItem' | 'setItem'> {
  const values = new Map<string, string>();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => {
      values.set(key, value);
    },
  };
}

describe('composer-runtime-prefs thread isolation', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }));
  });

  it('isolates runtime_target and model per conversation thread', () => {
    const storage = memoryStorage();
    writeComposerRuntimePrefs(
      'workspace_a',
      { runtime_target: 'cursor_local', cursor_cli_model: 'composer-2.5-fast' },
      'thread_1',
      storage,
    );
    writeComposerRuntimePrefs(
      'workspace_a',
      { runtime_target: 'claude_local', claude_cli_model: 'sonnet-4' },
      'thread_2',
      storage,
    );

    expect(readComposerRuntimePrefs('workspace_a', 'thread_1', storage)).toEqual({
      runtime_target: 'cursor_local',
      cursor_cli_model: 'composer-2.5-fast',
    });
    expect(readComposerRuntimePrefs('workspace_a', 'thread_2', storage)).toEqual({
      runtime_target: 'claude_local',
      claude_cli_model: 'sonnet-4',
    });
  });

  it('falls back to legacy workspace-only prefs when thread has no entry', () => {
    const storage = memoryStorage();
    writeComposerRuntimePrefs(
      'workspace_a',
      {
        runtime_target: 'codex_local',
        codex_cli_model: 'gpt-5',
      },
      null,
      storage,
    );
    expect(readComposerRuntimePrefs('workspace_a', 'thread_new', storage)).toEqual({
      runtime_target: 'codex_local',
      codex_cli_model: 'gpt-5',
    });
  });
});
