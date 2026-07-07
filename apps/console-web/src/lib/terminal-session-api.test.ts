import { describe, expect, it } from 'vitest';

import { buildTerminalWebSocketUrl } from './terminal-session-api';

describe('buildTerminalWebSocketUrl', () => {
  it('builds a websocket URL from an explicit control-plane base URL', () => {
    expect(
      buildTerminalWebSocketUrl('workspace_alpha', { baseUrl: 'http://127.0.0.1:8787' }),
    ).toBe(
      'ws://127.0.0.1:8787/api/workspaces/workspace_alpha/terminal?session_id=terminal-operator&role=operator',
    );
  });

  it('escapes workspace identifiers in the path', () => {
    expect(
      buildTerminalWebSocketUrl('workspace beta', { baseUrl: 'http://127.0.0.1:8787' }),
    ).toBe(
      'ws://127.0.0.1:8787/api/workspaces/workspace%20beta/terminal?session_id=terminal-operator&role=operator',
    );
  });

  it('includes custom session identity in the query string', () => {
    expect(
      buildTerminalWebSocketUrl('workspace_alpha', {
        baseUrl: 'http://127.0.0.1:8787',
        sessionId: 'terminal-agent-run1',
        role: 'agent',
      }),
    ).toBe(
      'ws://127.0.0.1:8787/api/workspaces/workspace_alpha/terminal?session_id=terminal-agent-run1&role=agent',
    );
  });
});
