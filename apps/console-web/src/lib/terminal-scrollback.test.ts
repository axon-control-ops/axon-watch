import { beforeEach, describe, expect, it } from 'vitest';

import {
  isShellPromptLine,
  migrateTerminalScrollback,
  sanitizeScrollbackText,
  scrollbackStorageKey,
} from './terminal-scrollback';

const sessionStorageMock = (() => {
  let store = new Map<string, string>();
  return {
    clear() {
      store = new Map<string, string>();
    },
    getItem(key: string) {
      return store.get(key) ?? null;
    },
    key(index: number) {
      return Array.from(store.keys())[index] ?? null;
    },
    get length() {
      return store.size;
    },
    removeItem(key: string) {
      store.delete(key);
    },
    setItem(key: string, value: string) {
      store.set(key, value);
    },
  } satisfies Storage;
})();

beforeEach(() => {
  Object.defineProperty(globalThis, 'sessionStorage', {
    configurable: true,
    value: sessionStorageMock,
  });
  sessionStorageMock.clear();
});

describe('terminal-scrollback', () => {
  it('removes scaffold status lines from persisted scrollback', () => {
    const cleaned = sanitizeScrollbackText(
      [
        '[terminal] Connecting backend PTY for workspace_smoke...',
        '[attached] workspace=workspace_smoke root=/tmp/workspace_smoke',
        'curl -s http://127.0.0.1:8787/api/runs',
        '[terminal] disconnected from backend shell.',
      ].join('\n'),
    );

    expect(cleaned).toBe('curl -s http://127.0.0.1:8787/api/runs');
  });

  it('removes shell prompt lines from scrollback', () => {
    const cleaned = sanitizeScrollbackText(
      [
        'edp@edudashpro:~/axon-nvme/repos/axon-watch$ ls',
        'README.md',
        'edp@edudashpro:~/axon-nvme/repos/axon-watch$',
      ].join('\n'),
    );

    expect(cleaned).toBe(
      [
        'edp@edudashpro:~/axon-nvme/repos/axon-watch$ ls',
        'README.md',
      ].join('\n'),
    );
  });

  it('drops concatenated prompt-only lines from workspace switches', () => {
    const noisy =
      'edp@edudashpro:~/axon-nvme/repos/axon-watch$ edp@edudashpro:~/axon-nvme/repos/axon-local$ edp@edudashpro:~/axon-nvme/repos/axon-watch$';

    expect(isShellPromptLine(noisy)).toBe(true);
    expect(sanitizeScrollbackText(['git status', noisy].join('\n'))).toBe('git status');
  });

  it('preserves current scrollback key during migration cleanup', () => {
    sessionStorage.setItem(scrollbackStorageKey('workspace_alpha', 'terminal-1'), 'persist me');

    migrateTerminalScrollback('workspace_alpha', 'terminal-1');

    expect(sessionStorage.getItem(scrollbackStorageKey('workspace_alpha', 'terminal-1'))).toBe(
      'persist me',
    );
  });
});
