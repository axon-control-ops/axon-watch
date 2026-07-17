import { describe, expect, it } from 'vitest';

import {
  ideActivityBarTerminalAriaLabel,
  ideActivityBarTerminalTitle,
  operatorTerminalChipLabel,
  operatorTerminalDockActionLabel,
  workbenchTerminalPanelAlive,
  workbenchTerminalPanelAriaLabel,
  workbenchTerminalPanelTitle,
  workbenchTerminalReopenAriaLabel,
  workbenchTerminalReopenTitle,
} from './workbench-terminal-panel-view';

describe('workbench terminal panel view', () => {
  it('names show and hide controls with the terminal shortcut', () => {
    expect(workbenchTerminalPanelTitle(false)).toBe('Show terminal panel (Ctrl/Cmd+J)');
    expect(workbenchTerminalPanelTitle(true)).toBe('Hide terminal panel (Ctrl/Cmd+J)');
    expect(workbenchTerminalPanelAriaLabel(false)).toBe('Show terminal panel');
    expect(workbenchTerminalPanelAriaLabel(true)).toBe('Hide terminal panel');
  });

  it('uses a compact operator chip label with the terminal shortcut when collapsed', () => {
    expect(operatorTerminalChipLabel(false)).toBe('Open terminal · Ctrl/Cmd+J');
    expect(operatorTerminalChipLabel(true)).toBe('Terminal open');
  });

  it('names the mission-control terminal dock footer action', () => {
    expect(operatorTerminalDockActionLabel(false)).toBe('Show · Ctrl/Cmd+J');
    expect(operatorTerminalDockActionLabel(true)).toBe('Hide');
  });

  it('names the IDE activity-bar terminal button with collapse hints', () => {
    expect(ideActivityBarTerminalTitle(false)).toBe('Terminal (Ctrl/Cmd+J)');
    expect(ideActivityBarTerminalTitle(true)).toBe(
      'Terminal (Ctrl/Cmd+J) · Click to collapse',
    );
    expect(ideActivityBarTerminalAriaLabel(false)).toBe('Expand terminal panel');
    expect(ideActivityBarTerminalAriaLabel(true)).toBe('Collapse terminal panel');
  });

  it('adds run context to hidden terminal controls', () => {
    expect(workbenchTerminalPanelTitle(false, 'executing')).toContain('Run in progress');
    expect(workbenchTerminalPanelAriaLabel(false, 'review_ready')).toContain('review ready');
    expect(ideActivityBarTerminalTitle(false, 'executing')).toContain('Run in progress');
    expect(ideActivityBarTerminalAriaLabel(false, 'review_ready')).toContain('review ready');
    expect(workbenchTerminalPanelAlive('executing')).toBe(true);
    expect(workbenchTerminalPanelAlive('review_ready')).toBe(true);
    expect(workbenchTerminalPanelAlive(null)).toBe(false);
  });

  it('names the workbench terminal reopen strip with run context', () => {
    expect(workbenchTerminalReopenTitle({ runPhase: null })).toBe(
      'Show terminal panel (Ctrl/Cmd+J)',
    );
    expect(workbenchTerminalReopenTitle({ runPhase: 'executing' })).toContain(
      'Run in progress',
    );
    expect(workbenchTerminalReopenAriaLabel({ runPhase: 'review_ready' })).toContain(
      'review ready',
    );
  });
});
