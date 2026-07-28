import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  pendingAgentBackgroundCommand,
  queueAgentBackgroundCommand,
} from './agent-shell-mirror-state';
import { flushPendingAgentBackgroundTerminalCommand } from './workbench-terminal-pending-commands';

describe('agent terminal pending commands', () => {
  beforeEach(() => {
    pendingAgentBackgroundCommand.value = null;
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      callback(0);
      return 1;
    });
  });

  it('uses the explicit agent run-command protocol, not interactive input', () => {
    const runCommand = vi.fn();
    const writeInput = vi.fn();
    const exitMirrorMode = vi.fn();
    queueAgentBackgroundCommand('npm run ota:canary');

    flushPendingAgentBackgroundTerminalCommand({
      sessions: [{ id: 'terminal-agent', role: 'agent' }],
      activeSessionId: 'terminal-agent',
      hosts: {
        'terminal-agent': { runCommand, writeInput, exitMirrorMode },
      },
      setVisibleSessionIds: vi.fn(),
    });

    expect(exitMirrorMode).toHaveBeenCalledOnce();
    expect(runCommand).toHaveBeenCalledWith('npm run ota:canary');
    expect(writeInput).not.toHaveBeenCalled();
    expect(pendingAgentBackgroundCommand.value).toBeNull();
  });
});
