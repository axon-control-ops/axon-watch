import { describe, expect, it } from 'vitest';

import {
  decideStaleIdeStreamSettle,
  listReattachIdeStreamThreadIds,
  listStaleIdeStreamThreadIds,
} from './stale-ide-stream-ui';

describe('stale-ide-stream-ui', () => {
  it('reattaches orphaned chrome when the linked run is still executing', () => {
    expect(
      decideStaleIdeStreamSettle({
        active: true,
        hasLiveSession: false,
        ideAgentRunId: 'run_1',
        runPhase: 'executing',
        runsLoaded: true,
      }),
    ).toBe('reattach');
  });

  it('settles orphaned chrome when the linked run is terminal', () => {
    expect(
      decideStaleIdeStreamSettle({
        active: true,
        hasLiveSession: false,
        ideAgentRunId: 'run_1',
        runPhase: 'completed',
        runsLoaded: true,
      }),
    ).toBe('settle');
  });

  it('settles orphaned Ask chrome with no run link', () => {
    expect(
      decideStaleIdeStreamSettle({
        active: true,
        hasLiveSession: false,
        ideAgentRunId: null,
        runPhase: null,
        runsLoaded: true,
      }),
    ).toBe('settle');
  });

  it('keeps a live Ask stream without a run link', () => {
    expect(
      decideStaleIdeStreamSettle({
        active: true,
        hasLiveSession: true,
        ideAgentRunId: null,
        runPhase: null,
        runsLoaded: true,
      }),
    ).toBe('keep');
  });

  it('settles when the linked run is idle or missing after runs load', () => {
    expect(
      decideStaleIdeStreamSettle({
        active: true,
        hasLiveSession: true,
        ideAgentRunId: 'run_1',
        runPhase: 'completed',
        runsLoaded: true,
      }),
    ).toBe('settle');
    expect(
      decideStaleIdeStreamSettle({
        active: true,
        hasLiveSession: true,
        ideAgentRunId: 'run_gone',
        runPhase: null,
        runsLoaded: true,
      }),
    ).toBe('settle');
  });

  it('lists stale and reattach thread ids from the stream ui map', () => {
    const input = {
      streamUiByThreadId: {
        thread_live: { active: true, ideAgentRunId: 'run_live' },
        thread_orphan: { active: true, ideAgentRunId: 'run_orphan' },
        thread_done: { active: true, ideAgentRunId: 'run_done' },
        thread_idle: { active: false, ideAgentRunId: null },
      },
      liveSessionThreadIds: new Set(['thread_live', 'thread_done']),
      runPhaseById: {
        run_live: 'executing',
        run_orphan: 'executing',
        run_done: 'completed',
      },
      runsLoaded: true,
    };
    expect(listStaleIdeStreamThreadIds(input)).toEqual(['thread_done']);
    expect(listReattachIdeStreamThreadIds(input)).toEqual(['thread_orphan']);
  });
});
