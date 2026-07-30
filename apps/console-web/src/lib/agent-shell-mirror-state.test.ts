import { describe, expect, it } from 'vitest';

import {
  armAgentShellMirror,
  agentShellMirrorActive,
  agentShellMirrorForcedText,
  clearAgentShellMirror,
  clearAgentShellMirrorForcedText,
  pendingAgentBackgroundCommand,
  queueAgentBackgroundCommand,
  queueAgentShellMirrorText,
  takePendingAgentBackgroundCommand,
} from './agent-shell-mirror-state';

describe('agent shell mirror state', () => {
  it('queues forced shell text and arms the mirror', () => {
    clearAgentShellMirror();
    clearAgentShellMirrorForcedText();

    queueAgentShellMirrorText('$ curl localhost\nok');

    expect(agentShellMirrorActive.value).toBe(true);
    expect(agentShellMirrorForcedText.value).toBe('$ curl localhost\nok\n');

    clearAgentShellMirror();
    clearAgentShellMirrorForcedText();
    armAgentShellMirror();
    expect(agentShellMirrorActive.value).toBe(true);
    clearAgentShellMirror();
  });

  it('queues commands into the agent terminal and clears the mirror', () => {
    armAgentShellMirror();
    queueAgentShellMirrorText('$ npm run ota:canary\nbuilding…');
    expect(agentShellMirrorActive.value).toBe(true);

    queueAgentBackgroundCommand('npm run ota:canary');

    expect(agentShellMirrorActive.value).toBe(false);
    expect(agentShellMirrorForcedText.value).toBeNull();
    expect(pendingAgentBackgroundCommand.value).toBe('npm run ota:canary');
    expect(takePendingAgentBackgroundCommand()).toBe('npm run ota:canary');
    expect(pendingAgentBackgroundCommand.value).toBeNull();
  });
});
