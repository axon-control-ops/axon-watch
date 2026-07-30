import { describe, expect, it } from 'vitest';

import {
  resolveAttentionFocusScrollTarget,
  resolveDefaultHighlightedSignalId,
} from './ide-attention-focus';

describe('ide-attention-focus', () => {
  it('routes IDE attention focus to the IDE panel anchor', () => {
    expect(resolveAttentionFocusScrollTarget('ide')).toBe('ide-attention-panel');
    expect(resolveAttentionFocusScrollTarget('operator')).toBe('mission-control-attention');
  });

  it('prefers an explicit signal id when provided', () => {
    expect(
      resolveDefaultHighlightedSignalId(
        [{ signal_id: 'signal_a', title: 'Signal A' }],
        'signal_b',
      ),
    ).toBe('signal_b');
  });

  it('falls back to bootstrap or single-signal defaults', () => {
    expect(
      resolveDefaultHighlightedSignalId([
        {
          signal_id: 'signal_watch_bootstrap_ready',
          title: 'Watch bootstrap ready',
        },
        { signal_id: 'signal_monitor', title: 'DashPro monitor critical' },
      ]),
    ).toBe('signal_watch_bootstrap_ready');

    expect(
      resolveDefaultHighlightedSignalId([
        { signal_id: 'signal_monitor', title: 'DashPro monitor critical' },
      ]),
    ).toBe('signal_monitor');

    expect(
      resolveDefaultHighlightedSignalId([
        { signal_id: 'signal_a', title: 'Signal A' },
        { signal_id: 'signal_b', title: 'Signal B' },
      ]),
    ).toBeNull();
  });
});
