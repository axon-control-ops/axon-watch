import { describe, expect, it } from 'vitest';

import {
  agentContentLooksLikeErrorDump,
  formatThreadRole,
  formatThreadTimestamp,
  shortenRunId,
  shouldCollapseSystemMessage,
  summarizeAgentErrorContent,
} from './thread-message-view';

describe('thread-message-view', () => {
  it('formats thread roles for compact labels', () => {
    expect(formatThreadRole('operator')).toBe('OP');
    expect(formatThreadRole('agent')).toBe('AGENT');
    expect(formatThreadRole('system')).toBe('SYSTEM');
  });

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

  it('does not treat long markdown agent replies as error dumps', () => {
    const content = ['## Summary', '', ...Array.from({ length: 120 }, () => '- [link](https://example.com)')].join(
      '\n',
    );
    expect(content.length).toBeGreaterThan(1800);
    expect(agentContentLooksLikeErrorDump(content)).toBe(false);
  });

  it('still flags large JSON array dumps as error dumps', () => {
    const content = `[${Array.from({ length: 400 }, (_, index) => `"item-${index}"`).join(',')}]`;
    expect(content.length).toBeGreaterThan(1800);
    expect(agentContentLooksLikeErrorDump(content)).toBe(true);
  });

  it('collapses noisy dispatch system acks', () => {
    expect(
      shouldCollapseSystemMessage('Run run_abc123 dispatched for workspace bootstrap-model'),
    ).toBe(true);
    expect(
      shouldCollapseSystemMessage('Command linked to run run_abc123 (phase executing).'),
    ).toBe(true);
  });
});
