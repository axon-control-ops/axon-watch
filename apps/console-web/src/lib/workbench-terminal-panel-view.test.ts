import { describe, expect, it } from 'vitest';

import {
  operatorTerminalChipLabel,
  operatorTerminalDockActionLabel,
  workbenchTerminalPanelAriaLabel,
  workbenchTerminalPanelTitle,
} from './workbench-terminal-panel-view';

describe('workbench terminal panel view', () => {
  it('names show/hide controls with the Ctrl/Cmd+J shortcut', () => {
    expect(workbenchTerminalPanelTitle(false)).toBe('Show terminal panel (Ctrl/Cmd+J)');
    expect(workbenchTerminalPanelTitle(true)).toBe('Hide terminal panel (Ctrl/Cmd+J)');
    expect(workbenchTerminalPanelAriaLabel(false)).toBe('Show terminal panel');
    expect(workbenchTerminalPanelAriaLabel(true)).toBe('Hide terminal panel');
  });

  it('surfaces the shortcut on Mission Control reopen affordances', () => {
    expect(operatorTerminalChipLabel(false)).toContain('Ctrl/Cmd+J');
    expect(operatorTerminalChipLabel(true)).toBe('Terminal open');
    expect(operatorTerminalDockActionLabel(false)).toContain('Ctrl/Cmd+J');
    expect(operatorTerminalDockActionLabel(true)).toBe('Hide');
  });
});
