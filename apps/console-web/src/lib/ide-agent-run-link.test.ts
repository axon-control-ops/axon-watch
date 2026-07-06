import { describe, expect, it } from 'vitest';

import type { RunRecord } from '../contracts/canonical';
import { resolveIdeAgentLinkedRunId } from './ide-agent-run-link';

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

  it('links only reusable agent phases', () => {
    const runs = [run({ run_id: 'run_a', phase: 'review_ready' })];
    expect(resolveIdeAgentLinkedRunId('run_a', runs)).toBe('run_a');
    expect(resolveIdeAgentLinkedRunId('run_missing', runs)).toBeNull();
  });

  it('drops terminal runs from the link', () => {
    const runs = [run({ run_id: 'run_done', phase: 'completed' })];
    expect(resolveIdeAgentLinkedRunId('run_done', runs)).toBeNull();
  });
});
