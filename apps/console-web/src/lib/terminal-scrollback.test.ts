import { describe, expect, it } from 'vitest';

import { sanitizeScrollbackText } from './terminal-scrollback';

describe('terminal-scrollback', () => {
  it('removes scaffold status lines from persisted scrollback', () => {
    const cleaned = sanitizeScrollbackText(
      [
        '[terminal] Connecting backend PTY for workspace_smoke...',
        '[attached] workspace=workspace_smoke root=/tmp/workspace_smoke',
        'curl -s http://127.0.0.1:8787/api/runs',
        '[terminal] disconnected from backend shell.',
      ].join('\n'),
    );

    expect(cleaned).toBe('curl -s http://127.0.0.1:8787/api/runs');
  });
});
