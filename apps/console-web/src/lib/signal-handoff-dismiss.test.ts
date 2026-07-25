import { describe, expect, it } from 'vitest';

import {
  canVerifyDismissHandoffSignal,
  isMonitorSignalId,
  isSignalOpenInInbox,
  linkedMonitorCheckId,
  monitorSignalIdsForCheck,
} from './signal-handoff-dismiss';

describe('signal-handoff-dismiss', () => {
  it('detects monitor signal ids and linked check ids', () => {
    expect(isMonitorSignalId('signal_monitor_dashpro_sentry_recent_issues_critical')).toBe(true);
    expect(linkedMonitorCheckId('signal_monitor_dashpro_sentry_recent_issues_critical')).toBe(
      'dashpro_sentry_recent_issues',
    );
    expect(monitorSignalIdsForCheck('dashpro_sentry_recent_issues')).toEqual([
      'signal_monitor_dashpro_sentry_recent_issues_critical',
      'signal_monitor_dashpro_sentry_recent_issues_warning',
    ]);
  });

  it('blocks verify dismiss while the monitor signal is still open', () => {
    const signalId = 'signal_monitor_dashpro_sentry_recent_issues_critical';
    expect(
      canVerifyDismissHandoffSignal(signalId, [{ signal_id: signalId }]).allowed,
    ).toBe(false);
    expect(canVerifyDismissHandoffSignal(signalId, []).allowed).toBe(true);
  });

  it('tracks open inbox membership', () => {
    expect(
      isSignalOpenInInbox('signal_a', [{ signal_id: 'signal_a' }, { signal_id: 'signal_b' }]),
    ).toBe(true);
    expect(isSignalOpenInInbox('signal_c', [{ signal_id: 'signal_a' }])).toBe(false);
  });
});
