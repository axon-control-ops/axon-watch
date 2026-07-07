import { describe, expect, it } from 'vitest';

import type { OperatorThreadEntry } from './operator-thread';
import {
  buildOperatorConversationDisplay,
  collapseRepeatedOperatorCommands,
  parseCommandExecutionContent,
  prepareOperatorConversationDock,
} from './operator-conversation-view';

function entry(
  role: OperatorThreadEntry['role'],
  content: string,
  overrides: Partial<OperatorThreadEntry> = {},
): OperatorThreadEntry {
  return {
    message_id: `message_${role}_${Math.random().toString(16).slice(2, 8)}`,
    thread_id: 'thread_test',
    run_id: 'run_test123',
    workspace_id: 'workspace_axon_watch',
    role,
    content,
    created_at: '2026-07-06T17:00:00Z',
    ...overrides,
  };
}

describe('operator-conversation-view', () => {
  it('parses command execution agent replies', () => {
    const parsed = parseCommandExecutionContent(
      'Executed `git_status` (ok) for run run_abc.\n\n```\n## dev\n M file.py\n```\n\nPhase is now completed.',
    );
    expect(parsed).toEqual({
      intent: 'git_status',
      status: 'ok',
      runId: 'run_abc',
      output: '## dev\n M file.py',
      footer: 'Phase is now completed.',
    });
  });

  it('compacts operator/system/agent command triplets into one card', () => {
    const messages = [
      entry('operator', 'git status'),
      entry('system', 'Run run_abc dispatched · phase review_ready · executed git_status (ok)'),
      entry(
        'agent',
        'Executed `git_status` (ok) for run run_abc.\n\n```\n## dev\n```\n\nReview when ready.',
      ),
      entry('operator', 'Real chat question'),
      entry('agent', 'Here is the answer.'),
    ];

    const display = buildOperatorConversationDisplay(messages);
    expect(display).toHaveLength(3);
    expect(display[0]).toMatchObject({
      kind: 'command_turn',
      command: 'git status',
      execution: {
        intent: 'git_status',
        output: '## dev',
      },
    });
    expect(display[1]).toMatchObject({
      kind: 'message',
      message: { role: 'operator', content: 'Real chat question' },
    });
    expect(display[2]).toMatchObject({
      kind: 'message',
      message: { role: 'agent', content: 'Here is the answer.' },
    });
  });

  it('drops standalone dispatch ack system lines', () => {
    const display = buildOperatorConversationDisplay([
      entry('system', 'Run run_abc dispatched · phase review_ready · executed git_status (ok)'),
      entry('operator', 'hello'),
    ]);
    expect(display).toHaveLength(1);
    expect(display[0]?.kind).toBe('message');
  });

  it('collapses repeated verification commands to the latest turn', () => {
    const messages = [
      entry('operator', 'git status'),
      entry('system', 'Run run_a dispatched · phase review_ready · executed git_status (ok)'),
      entry(
        'agent',
        'Executed `git_status` (ok) for run run_a.\n\n```\nold\n```\n\nReview when ready.',
      ),
      entry('operator', 'git status'),
      entry('system', 'Run run_b dispatched · phase review_ready · executed git_status (ok)'),
      entry(
        'agent',
        'Executed `git_status` (ok) for run run_b.\n\n```\nnew\n```\n\nReview when ready.',
      ),
    ];
    const collapsed = collapseRepeatedOperatorCommands(buildOperatorConversationDisplay(messages));
    expect(collapsed).toHaveLength(1);
    expect(collapsed[0]).toMatchObject({
      kind: 'command_turn',
      command: 'git status',
      repeatCount: 2,
      compact: true,
      execution: { output: 'new' },
    });
  });

  it('prepares a trimmed operator dock with a history banner', () => {
    const makeTriplet = (command: string, runId: string, output: string): OperatorThreadEntry[] => [
      entry('operator', command),
      entry('system', `Run ${runId} dispatched · phase review_ready · executed git_status (ok)`),
      entry(
        'agent',
        'Executed `git_status` (ok) for run ' +
          `${runId}.\n\n` +
          '```\n' +
          `${output}\n` +
          '```\n\nReview when ready.',
      ),
    ];

    const messages = [
      ...makeTriplet('git status', 'run_a', 'branch-a'),
      ...makeTriplet('check-health', 'run_b', 'branch-b'),
      ...makeTriplet('run npm test', 'run_c', 'branch-c'),
      ...makeTriplet('run ./scripts/dev/check-health.sh', 'run_d', 'branch-d'),
    ];

    const dock = prepareOperatorConversationDock(messages, { maxItems: 2 });
    expect(buildOperatorConversationDisplay(messages)).toHaveLength(4);
    expect(dock.hiddenCount).toBe(2);
    expect(dock.items[0]?.kind).toBe('dock_banner');
    expect(dock.items.filter((item) => item.kind === 'command_turn')).toHaveLength(2);
  });
});
