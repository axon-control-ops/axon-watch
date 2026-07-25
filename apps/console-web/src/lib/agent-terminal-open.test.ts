import { describe, expect, it, beforeEach } from 'vitest';

import {
  agentShellMirrorActive,
  agentShellMirrorForcedText,
  clearAgentShellMirror,
  clearAgentShellMirrorForcedText,
} from './agent-shell-mirror-state';
import { prepareAgentTerminalOpen } from './agent-terminal-open';

describe('prepareAgentTerminalOpen', () => {
  beforeEach(() => {
    clearAgentShellMirror();
    clearAgentShellMirrorForcedText();
  });

  it('arms live mirror without freezing a snapshot for open shells', () => {
    expect(
      prepareAgentTerminalOpen({
        command: 'gh run watch 1',
        output: 'watching…',
        open: true,
      }),
    ).toBe('live');
    expect(agentShellMirrorActive.value).toBe(true);
    expect(agentShellMirrorForcedText.value).toBeNull();
  });

  it('pins a closed shell snapshot so the idle agent PTY cannot replace it', () => {
    expect(
      prepareAgentTerminalOpen({
        command: 'gh run watch 1',
        output: 'completed',
        open: false,
      }),
    ).toBe('pinned');
    expect(agentShellMirrorActive.value).toBe(true);
    expect(agentShellMirrorForcedText.value).toContain('$ gh run watch 1');
    expect(agentShellMirrorForcedText.value).toContain('completed');
  });
});
