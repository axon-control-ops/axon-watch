import { describe, expect, it } from 'vitest';

import type { RunRecord } from '../contracts/canonical';
import { resolveIdeAgentLinkedRunId, resolveIdeAgentLinkedRunIdFromMessages } from './ide-agent-run-link';

function run(partial: Partial<RunRecord> & Pick<RunRecord, 'run_id' | 'phase'>): RunRecord {
  return {
    workspace_id: 'ws_alpha',
    mode: 'agent',
    summary: 'test',
    can_approve: false,
    ...partial,
  } as RunRecord;
}

describe('resolveIdeAgentLinkedRunId', () => {
  it('returns null when no stored run id', () => {
    expect(resolveIdeAgentLinkedRunId(null, [])).toBeNull();
  });

  it('links reusable run phases including in-progress Plan runs', () => {
    const runs = [
      run({ run_id: 'run_a', phase: 'review_ready' }),
      run({ run_id: 'run_plan', phase: 'planning', mode: 'plan' }),
    ];
    expect(resolveIdeAgentLinkedRunId('run_a', runs)).toBe('run_a');
    expect(
      resolveIdeAgentLinkedRunId('run_plan', runs, { expectedMode: 'plan' }),
    ).toBe('run_plan');
    expect(resolveIdeAgentLinkedRunId('run_missing', runs)).toBeNull();
  });

  it('drops terminal runs from the link', () => {
    const runs = [run({ run_id: 'run_done', phase: 'completed' })];
    expect(resolveIdeAgentLinkedRunId('run_done', runs)).toBeNull();
  });

  it('does not link an agent run when debug mode is expected', () => {
    const runs = [run({ run_id: 'run_agent', phase: 'review_ready', mode: 'agent' })];
    expect(resolveIdeAgentLinkedRunId('run_agent', runs, { expectedMode: 'debug' })).toBeNull();
    expect(resolveIdeAgentLinkedRunId('run_agent', runs, { expectedMode: 'agent' })).toBe('run_agent');
  });

  it('links a debug run when debug mode is expected', () => {
    const runs = [run({ run_id: 'run_debug', phase: 'review_ready', mode: 'debug' })];
    expect(resolveIdeAgentLinkedRunId('run_debug', runs, { expectedMode: 'debug' })).toBe(
      'run_debug',
    );
  });

  it('restores the latest reusable run from thread history', () => {
    const runs = [
      run({ run_id: 'run_done', phase: 'completed' }),
      run({ run_id: 'run_live', phase: 'review_ready' }),
    ];
    expect(
      resolveIdeAgentLinkedRunIdFromMessages(
        [
          {
            message_id: 'msg_1',
            thread_id: 'thread_1',
            workspace_id: 'ws_alpha',
            run_id: 'run_done',
            role: 'operator',
            content: 'older',
            created_at: '2026-07-07T00:00:00Z',
          },
          {
            message_id: 'msg_2',
            thread_id: 'thread_1',
            workspace_id: 'ws_alpha',
            run_id: 'run_live',
            role: 'agent',
            content: 'latest',
            created_at: '2026-07-07T00:01:00Z',
          },
        ],
        runs,
      ),
    ).toBe('run_live');
  });
});
