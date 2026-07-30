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

  it('prefers actionable signals over bootstrap summaries', () => {
    expect(
      resolveDefaultHighlightedSignalId([
        {
          signal_id: 'signal_watch_bootstrap_ready',
          title: 'Watch bootstrap ready',
        },
        { signal_id: 'signal_monitor', title: 'DashPro monitor critical' },
      ]),
    ).toBe('signal_monitor');

    expect(
      resolveDefaultHighlightedSignalId([
        { signal_id: 'signal_monitor', title: 'DashPro monitor critical' },
      ]),
    ).toBe('signal_monitor');

  });

  it('uses the spoken signal, then highest severity, when attention has multiple items', () => {
    const signals = [
      { signal_id: 'signal_warning', title: 'Warning', severity: 'warning' },
      { signal_id: 'signal_critical', title: 'Critical', severity: 'critical' },
    ];
    expect(
      resolveDefaultHighlightedSignalId(signals, null, 'signal_warning'),
    ).toBe('signal_warning');
    expect(resolveDefaultHighlightedSignalId(signals)).toBe('signal_critical');
  });
});
