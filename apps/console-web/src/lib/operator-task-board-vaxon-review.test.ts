import { describe, expect, it } from 'vitest';

import { resolveVaxonReviewTarget } from './operator-task-board-vaxon-review';

describe('resolveVaxonReviewTarget', () => {
  it('opens the handoff thread when Lead has posted a rollup', () => {
    const target = resolveVaxonReviewTarget({
      vaxon_handoff: { thread_id: 'thread_abc', message_id: 'message_xyz' },
    });
    expect(target).toEqual({ kind: 'open_thread', threadId: 'thread_abc' });
  });

  it('reports not_ready when no handoff has been posted yet', () => {
    const target = resolveVaxonReviewTarget({ vaxon_handoff: null });
    expect(target.kind).toBe('not_ready');
  });

  it('reports not_ready when vaxon_handoff is absent entirely', () => {
    const target = resolveVaxonReviewTarget({});
    expect(target.kind).toBe('not_ready');
  });

  it('reports not_ready for a null/undefined plan (fetch failure upstream)', () => {
    expect(resolveVaxonReviewTarget(null).kind).toBe('not_ready');
    expect(resolveVaxonReviewTarget(undefined).kind).toBe('not_ready');
  });

  it('reports not_ready when thread_id is blank/whitespace', () => {
    const target = resolveVaxonReviewTarget({
      vaxon_handoff: { thread_id: '   ', message_id: 'message_xyz' },
    });
    expect(target.kind).toBe('not_ready');
  });
});
