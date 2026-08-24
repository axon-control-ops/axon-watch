import { describe, expect, it } from 'vitest';

import {
  buildSidebarAgentTranscriptLines,
  resolveSidebarAgentTranscript,
} from './sidebar-agent-transcript-view';

describe('buildSidebarAgentTranscriptLines', () => {
  it('maps thinking, tool, and edit segments into compact lines', () => {
    const lines = buildSidebarAgentTranscriptLines(
      [
        ':::thinking',
        'Checking Sentry for DashPro criticals.',
        ':::',
        ':::tool Read OPERATIONS.md',
        ':::edit src/App.vue +3 -1',
        '@@',
        '+ok',
        ':::',
      ].join('\n'),
    );
    expect(lines.map((line) => line.kind)).toEqual(['thinking', 'tool', 'edit']);
    expect(lines[0]?.text).toContain('Checking Sentry');
    expect(lines[1]?.text).toBe('Read OPERATIONS.md');
    expect(lines[2]?.text).toBe('Edited file: src/App.vue');
  });

  it('marks open thinking as live while streaming', () => {
    const lines = buildSidebarAgentTranscriptLines(
      [':::thinking', 'Still reading the ledger…'].join('\n'),
      { streaming: true },
    );
    expect(lines).toHaveLength(1);
    expect(lines[0]?.live).toBe(true);
  });
});

describe('resolveSidebarAgentTranscript', () => {
  it('prefers the active streaming agent message', () => {
    const view = resolveSidebarAgentTranscript({
      messages: [
        { message_id: 'old', role: 'agent', content: ':::thinking\nOld turn\n:::' },
        {
          message_id: 'live',
          role: 'agent',
          content: ':::thinking\nLive stream body\n',
        },
      ],
      agentStreamActive: true,
      agentStreamMessageId: 'live',
    });
    expect(view.messageId).toBe('live');
    expect(view.streaming).toBe(true);
    expect(view.lines[0]?.text).toContain('Live stream body');
  });

  it('returns an empty hint when there is no agent content yet', () => {
    const view = resolveSidebarAgentTranscript({
      messages: [],
      agentStreamActive: true,
      agentStreamMessageId: null,
    });
    expect(view.lines).toEqual([]);
    expect(view.emptyHint).toContain('Waiting');
  });
});
