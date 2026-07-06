import { describe, expect, it } from 'vitest';

import {
  agentContentLooksLikeErrorDump,
  formatThreadTimestamp,
  shortenRunId,
  summarizeAgentErrorContent,
} from './thread-message-view';

describe('thread-message-view', () => {
  it('formats timestamps for display', () => {
    const formatted = formatThreadTimestamp('2026-07-06T10:53:00.000Z');
    expect(formatted).not.toContain('2026-07-06T10:53:00.000Z');
  });

  it('shortens long run ids', () => {
    expect(shortenRunId('run_0123456789abcdef')).toBe('run_012345…');
  });

  it('detects error dumps and summarizes them', () => {
    const content = '401 Unauthorized\n{"error":{"message":"Incorrect API key"}}';
    expect(agentContentLooksLikeErrorDump(content)).toBe(true);
    expect(summarizeAgentErrorContent(content)).toContain('401 Unauthorized');
  });
});
