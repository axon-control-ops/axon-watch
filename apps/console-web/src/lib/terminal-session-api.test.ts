import { describe, expect, it } from 'vitest';

import { buildTerminalWebSocketUrl } from './terminal-session-api';

describe('buildTerminalWebSocketUrl', () => {
  it('builds a websocket URL from an explicit control-plane base URL', () => {
    expect(buildTerminalWebSocketUrl('workspace_alpha', 'http://127.0.0.1:8787')).toBe(
      'ws://127.0.0.1:8787/api/workspaces/workspace_alpha/terminal',
    );
  });

  it('escapes workspace identifiers in the path', () => {
    expect(buildTerminalWebSocketUrl('workspace beta', 'http://127.0.0.1:8787')).toBe(
      'ws://127.0.0.1:8787/api/workspaces/workspace%20beta/terminal',
    );
  });
});
