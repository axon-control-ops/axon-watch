import { describe, expect, it } from 'vitest';

import type { OperatorThreadEntry } from './operator-thread';
import { filterThreadMessagesForSurface } from './thread-surface-view';

let counter = 0;
function entry(role: OperatorThreadEntry['role'], content: string): OperatorThreadEntry {
  counter += 1;
  return {
    message_id: `message_${counter}`,
    role,
    content,
    created_at: '2026-07-06T17:00:00Z',
    run_id: null,
  } as OperatorThreadEntry;
}

describe('filterThreadMessagesForSurface (ide)', () => {
  it('drops Lane B plumbing system messages but keeps the conversation', () => {
    const messages = [
      entry('operator', 'Add a comment to README.md'),
      entry('system', 'Lane B (agent) — streaming runtime reply for run run_f7724c286ef2.'),
      entry('agent', 'Working on it.'),
      entry('system', 'Lane B (agent) recorded run run_abc at the approval boundary.'),
      entry('agent', 'Done.'),
    ];
    const filtered = filterThreadMessagesForSurface(messages, 'ide');
    expect(filtered.map((message) => message.role)).toEqual(['operator', 'agent', 'agent']);
  });

  it('still strips operator command turns from mixed legacy threads', () => {
    const messages = [
      entry('operator', 'git status'),
      entry('system', 'Run run_1 dispatched — phase review_ready — executed git_status (ok)'),
      entry('agent', 'clean tree'),
      entry('operator', 'Real IDE prompt'),
      entry('agent', 'Real IDE reply'),
    ];
    const filtered = filterThreadMessagesForSurface(messages, 'ide');
    expect(filtered.map((message) => message.content)).toEqual([
      'Real IDE prompt',
      'Real IDE reply',
    ]);
  });
});
