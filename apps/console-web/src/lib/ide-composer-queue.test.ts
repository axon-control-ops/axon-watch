import { describe, expect, it } from 'vitest';

import type { RunRecord } from '../contracts/canonical';

import {
  appendIdeComposerQueueEntry,
  findIdeComposerQueueEntry,
  ideComposerQueueScopeKey,
  removeIdeComposerQueueEntry,
  resolveIdeStopRun,
  shouldQueueIdeComposerSubmit,
  shiftIdeComposerQueue,
} from './ide-composer-queue';

const baseRun = (overrides: Partial<RunRecord>): RunRecord =>
  ({
    run_id: 'run_a',
    workspace_id: 'workspace_axon_watch',
    phase: 'executing',
    status: 'running',
    can_stop: true,
    can_resume: false,
    can_approve: false,
    current_step: 'Working',
    ...overrides,
  }) as RunRecord;

describe('ide composer queue', () => {
  it('isolates queues by workspace and active agent thread', () => {
    expect(ideComposerQueueScopeKey('workspace_tps', 'thread_noor')).toBe(
      'workspace_tps::thread_noor',
    );
    expect(ideComposerQueueScopeKey('workspace_tps', 'thread_vera')).toBe(
      'workspace_tps::thread_vera',
    );
    expect(ideComposerQueueScopeKey('workspace_tps', null)).toBe(
      'workspace_tps::workspace',
    );
    expect(ideComposerQueueScopeKey(null, 'thread_noor')).toBeNull();
  });

  it('resolves stoppable runs from linked, explicit, or primary ids', () => {
    expect(
      resolveIdeStopRun({
        linkedRun: baseRun({ run_id: 'run_linked' }),
        linkedRunId: null,
        runs: [],
        primaryRun: null,
        workspaceId: 'workspace_axon_watch',
      })?.run_id,
    ).toBe('run_linked');

    expect(
      resolveIdeStopRun({
        linkedRun: null,
        linkedRunId: 'run_explicit',
        runs: [baseRun({ run_id: 'run_explicit', can_stop: true })],
        primaryRun: null,
        workspaceId: 'workspace_axon_watch',
      })?.run_id,
    ).toBe('run_explicit');

    expect(
      resolveIdeStopRun({
        linkedRun: null,
        linkedRunId: null,
        runs: [],
        primaryRun: baseRun({ run_id: 'run_primary' }),
        workspaceId: 'workspace_axon_watch',
      })?.run_id,
    ).toBe('run_primary');

    expect(
      resolveIdeStopRun({
        linkedRun: null,
        linkedRunId: null,
        runs: [baseRun({ run_id: 'run_live' })],
        primaryRun: null,
        workspaceId: 'workspace_axon_watch',
      })?.run_id,
    ).toBe('run_live');
  });

  it('queues busy run-linked submits', () => {
    expect(
      shouldQueueIdeComposerSubmit({ agentBusy: true, composerMode: 'agent' }),
    ).toBe(true);
    expect(
      shouldQueueIdeComposerSubmit({ agentBusy: true, composerMode: 'debug' }),
    ).toBe(true);
    expect(
      shouldQueueIdeComposerSubmit({ agentBusy: true, composerMode: 'plan' }),
    ).toBe(true);
    expect(
      shouldQueueIdeComposerSubmit({ agentBusy: true, composerMode: 'ask' }),
    ).toBe(false);
    expect(
      shouldQueueIdeComposerSubmit({ agentBusy: false, composerMode: 'agent' }),
    ).toBe(false);
  });

  it('shifts and removes queued entries', () => {
    const queue = appendIdeComposerQueueEntry([], {
      id: 'q1',
      content: 'first',
      composerMode: 'agent',
      createdAt: '2026-07-08T00:00:00Z',
      threadId: 'thread_noor',
    });

    expect(shiftIdeComposerQueue(queue).next?.content).toBe('first');
    expect(removeIdeComposerQueueEntry(queue, 'q1')).toEqual([]);
  });

  it('finds a queued entry by id for edit', () => {
    const queue = appendIdeComposerQueueEntry([], {
      id: 'q1',
      content: 'revise me',
      composerMode: 'plan',
      createdAt: '2026-07-08T00:00:00Z',
      threadId: 'thread_noor',
    });

    expect(findIdeComposerQueueEntry(queue, 'q1')?.content).toBe('revise me');
    expect(findIdeComposerQueueEntry(queue, 'missing')).toBeNull();
  });
});
