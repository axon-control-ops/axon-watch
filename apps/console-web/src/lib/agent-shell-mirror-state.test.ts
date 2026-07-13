import { describe, expect, it } from 'vitest';

import {
  armAgentShellMirror,
  agentShellMirrorActive,
  agentShellMirrorForcedText,
  clearAgentShellMirror,
  clearAgentShellMirrorForcedText,
  queueAgentShellMirrorText,
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
});
