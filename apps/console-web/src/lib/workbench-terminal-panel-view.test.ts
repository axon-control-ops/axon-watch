import { describe, expect, it } from 'vitest';

import {
  ideActivityBarTerminalAriaLabel,
  ideActivityBarTerminalTitle,
  operatorTerminalChipLabel,
  operatorTerminalDockActionLabel,
  workbenchTerminalPanelAlive,
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

  it('adds run-phase hints when the terminal is hidden', () => {
    expect(workbenchTerminalPanelTitle(false, 'executing')).toContain('Run in progress');
    expect(workbenchTerminalPanelAlive('review_ready')).toBe(true);
    expect(ideActivityBarTerminalTitle(false, 'executing')).toContain('Run in progress');
    expect(ideActivityBarTerminalAriaLabel(false, 'review_ready')).toContain('review ready');
    expect(ideActivityBarTerminalTitle(true)).toContain('Click to collapse');
  });
});
