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

  it('returns child-project monitor hint copy with vault guidance', () => {
    expect(
      signalOperatorHint({
        signalId: 'signal_monitor_dashpro_sentry_recent_issues_warning',
        title: 'DashPro Sentry warning',
        meta: {
          signal_family: 'child_project_monitor',
          workspace_label: 'DashPro',
          monitor_status: 'warning',
        },
      }),
    ).toContain('/vault');
  });

  it('explains observe mode is not a button', () => {
    expect(watchRuleTooltip('observe')).toContain('informational only');
  });
});
