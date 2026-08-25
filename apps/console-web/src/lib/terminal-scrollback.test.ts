import { beforeEach, describe, expect, it } from 'vitest';

import {
  isShellPromptLine,
  migrateTerminalScrollback,
  sanitizeScrollbackText,
  sanitizeTerminalDisplayOutput,
  scrollbackStorageKey,
  stripOrphanAnsiFragments,
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

  it('strips Jest cursor-rewrite ANSI spam for readable cards', () => {
    const noisy = [
      '\u001b[1A\u001b[999D\u001b[K\u001b[1mTest Suites:\u001b[22m \u001b[1m\u001b[32m1 passed\u001b[39m',
      'PASS tests/unit/services/staffVisibility.test.ts',
      'Test Suites: 1 passed, 1 total',
      'Tests:       9 passed, 9 total',
    ].join('\n');
    const cleaned = sanitizeTerminalDisplayOutput(noisy, 'npm test -- tests/unit/foo.test.ts');
    expect(cleaned).toContain('PASS tests/unit/services/staffVisibility.test.ts');
    expect(cleaned).toContain('Test Suites: 1 passed, 1 total');
    expect(cleaned).not.toMatch(/\u001b\[/);
    expect(cleaned).not.toMatch(/\[1A|\[999D|\[32m/);
  });

  it('drops orphan [K-only lines when ESC bytes were lost in storage', () => {
    const noisy = ['[K', '[K', '[K', 'PASS tests/unit/foo.test.ts', '[K'].join('\n');
    const cleaned = sanitizeTerminalDisplayOutput(noisy, 'npm test');
    expect(cleaned).toBe('PASS tests/unit/foo.test.ts');
  });

  it('does not eat the leading letter of ordinary bracketed words', () => {
    // Regression: the orphan-CSI pattern matched "[o" inside "[operator_blocker]"
    // (zero digits before a letter looks the same as a real zero-param CSI final
    // byte like "[K"), corrupting structured agent replies such as Lead check-in
    // reports ("1. [operator_blocker] Noor (lead) last shift failed") into
    // "1. perator_blocker] Noor..." -- silently dropping every finding.
    const line = '1. [operator_blocker] Noor (lead) last shift failed (ESCALATE)';
    expect(stripOrphanAnsiFragments(line)).toBe(line);
    expect(stripOrphanAnsiFragments('detail [run=run_fc8014df7146] tail')).toBe(
      'detail [run=run_fc8014df7146] tail',
    );
  });

  it('still strips real orphan CSI fragments at a line/fragment boundary', () => {
    expect(stripOrphanAnsiFragments('[K')).toBe('');
    expect(stripOrphanAnsiFragments('[K\nPASS foo.test.ts')).toBe('\nPASS foo.test.ts');
    expect(stripOrphanAnsiFragments('[1A[999D[K PASS')).toBe(' PASS');
  });
});
