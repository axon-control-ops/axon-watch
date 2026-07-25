import { describe, expect, it } from 'vitest';

import { summarizeIdeAgentActivity } from './ide-agent-activity-view';

describe('summarizeIdeAgentActivity', () => {
  it('counts searches, files, terminals, and tools from transcript blocks', () => {
    const content = [
      ':::research cursor agent features',
      '- Cursor docs | https://cursor.com/docs',
      ':::',
      ':::edit README.md +2 -1',
      '+hello',
      ':::',
      ':::terminal npm test',
      'ok',
      ':::',
      ':::tool Shell',
    ].join('\n');

    const summary = summarizeIdeAgentActivity(content);
    expect(summary.searchCount).toBe(1);
    expect(summary.fileCount).toBe(1);
    expect(summary.terminalCount).toBe(1);
    expect(summary.toolCount).toBe(1);
    expect(summary.chips.map((chip) => chip.kind)).toEqual(['search', 'file', 'terminal', 'tool']);
  });
});
