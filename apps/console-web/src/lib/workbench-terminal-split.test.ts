import { describe, expect, it } from 'vitest';

import {
  clampWorkbenchTerminalHeight,
  DEFAULT_WORKBENCH_TERMINAL_HEIGHT,
  MAX_DEFAULT_WORKBENCH_TERMINAL_HEIGHT,
  MIN_WORKBENCH_TERMINAL_HEIGHT,
  readStoredWorkbenchTerminalPanelVisible,
  resolveDefaultWorkbenchTerminalHeight,
  workbenchTerminalPanelVisibleStorageKey,
} from './workbench-terminal-split';

describe('workbench terminal split', () => {
  it('clamps terminal height within min and container ratio', () => {
    expect(clampWorkbenchTerminalHeight(120, 900)).toBe(MIN_WORKBENCH_TERMINAL_HEIGHT);
    expect(clampWorkbenchTerminalHeight(900, 900)).toBe(792);
    expect(clampWorkbenchTerminalHeight(320, 900)).toBe(320);
  });

  it('falls back to default for invalid input', () => {
    expect(clampWorkbenchTerminalHeight(Number.NaN, 0)).toBe(DEFAULT_WORKBENCH_TERMINAL_HEIGHT);
  });

  it('resolves a lower responsive default height for fresh sessions', () => {
    expect(resolveDefaultWorkbenchTerminalHeight(0)).toBe(240);
    expect(resolveDefaultWorkbenchTerminalHeight(900)).toBe(240);
    expect(resolveDefaultWorkbenchTerminalHeight(1200)).toBe(MAX_DEFAULT_WORKBENCH_TERMINAL_HEIGHT);
    expect(resolveDefaultWorkbenchTerminalHeight(1200, 'operator')).toBeLessThanOrEqual(280);
  });

  it('defaults terminal panel visibility by layout mode outside the browser', () => {
    expect(readStoredWorkbenchTerminalPanelVisible('ide')).toBe(true);
    expect(readStoredWorkbenchTerminalPanelVisible('operator')).toBe(false);
  });

  it('uses mode-specific session keys', () => {
    expect(workbenchTerminalPanelVisibleStorageKey('operator')).toContain('operator');
    expect(workbenchTerminalPanelVisibleStorageKey('ide')).toContain('ide');
  });
});
