import { describe, expect, it } from 'vitest';

import {
  isBootstrapSummarySignal,
  signalOperatorHint,
  watchRuleTooltip,
} from './operator-signal-hints';

describe('operator-signal-hints', () => {
  it('detects bootstrap summary signals', () => {
    expect(
      isBootstrapSummarySignal('signal_runtime_summary_degraded', 'Bootstrap: runtime summary stale'),
    ).toBe(true);
  });

  it('returns bootstrap dev hint copy', () => {
    expect(
      signalOperatorHint({
        signalId: 'signal_runtime_summary_degraded',
        title: 'Bootstrap: runtime summary stale',
      }),
    ).toContain('Expected in local bootstrap');
  });

  it('explains observe mode is not a button', () => {
    expect(watchRuleTooltip('observe')).toContain('informational only');
  });
});
