import { describe, expect, it } from 'vitest';

import {
  resolveActiveVisibleTerminalSessionIds,
  resolveMirrorVisibleTerminalSessionIds,
} from './workbench-terminal-visible-panes';

describe('workbench-terminal-visible-panes', () => {
  it('mirrors agent shell into a single pane (no auto-split)', () => {
    expect(resolveMirrorVisibleTerminalSessionIds('terminal-vaxon')).toEqual([
      'terminal-vaxon',
    ]);
  });

  it('replaces a single visible pane when the active session changes', () => {
    expect(
      resolveActiveVisibleTerminalSessionIds({
        visibleSessionIds: ['terminal-bash'],
        existingSessionIds: new Set(['terminal-bash', 'terminal-vaxon']),
        activeSessionId: 'terminal-vaxon',
      }),
    ).toEqual(['terminal-vaxon']);
  });

  it('keeps an explicit split when swapping the inactive pane', () => {
    expect(
      resolveActiveVisibleTerminalSessionIds({
        visibleSessionIds: ['terminal-bash', 'terminal-other'],
        existingSessionIds: new Set([
          'terminal-bash',
          'terminal-other',
          'terminal-vaxon',
        ]),
        activeSessionId: 'terminal-vaxon',
      }),
    ).toEqual(['terminal-bash', 'terminal-vaxon']);
  });
});
