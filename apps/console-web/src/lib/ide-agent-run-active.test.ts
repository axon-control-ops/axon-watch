import { describe, expect, it } from 'vitest';

import type { RunRecord } from '../contracts/canonical';
import { shouldClearIdeAgentRunLink, shouldShowIdeAgentStop } from './ide-agent-run-active';

function run(partial: Partial<RunRecord>): RunRecord {
  return {
    run_id: 'run_test',
    workspace_id: 'workspace_alpha',
    lane_id: 'lane_b',
    mode: 'agent',
    status: 'running',
    phase: 'executing',
    summary: 'test',
    detail: '',
    started_at: '2026-07-07T16:00:00Z',
    updated_at: '2026-07-07T16:00:00Z',
    ended_at: null,
    can_stop: true,
    can_resume: false,
    can_approve: false,
    can_review: false,
    current_step: null,
    history_ref: 'history',
    ...partial,
  };
}

describe('ide-agent-run-active', () => {
  it('shows stop while the stream is active', () => {
    expect(shouldShowIdeAgentStop({ agentStreamActive: true, run: null })).toBe(true);
  });

  it('hides stop after the stream ends — including stuck executing runs', () => {
    expect(
      shouldShowIdeAgentStop({
        agentStreamActive: false,
        run: run({ phase: 'paused', status: 'waiting', can_stop: true }),
      }),
    ).toBe(false);
    expect(
      shouldShowIdeAgentStop({
        agentStreamActive: false,
        run: run({ phase: 'executing', status: 'running', can_stop: true }),
      }),
    ).toBe(false);
  });

  it('clears ide agent link when run is terminal', () => {
    expect(shouldClearIdeAgentRunLink(run({ phase: 'completed', status: 'done', can_stop: false }))).toBe(
      true,
    );
    expect(shouldClearIdeAgentRunLink(run({ phase: 'executing', status: 'running' }))).toBe(false);
  });
});
