import { describe, expect, it } from 'vitest';

import {
  countActionableOpenSignals,
  filterActionableOpenSignals,
  resolveOperatorSignalCount,
} from './operator-signal-count';

describe('operator-signal-count', () => {
  it('excludes bootstrap signals from actionable counts', () => {
    const items = [
      {
        signal_id: 'signal_watch_bootstrap_ready',
        title: 'Watch bootstrap ready',
        status: 'open',
      },
      {
        signal_id: 'signal_monitor_dashpro_sentry_recent_issues_critical',
        title: 'DashPro Sentry critical',
        status: 'open',
        workspace_id: 'workspace_dashpro',
      },
    ];

    expect(countActionableOpenSignals(items)).toBe(1);
  });

  it('scopes actionable counts to the active workspace', () => {
    const items = [
      {
        signal_id: 'signal_monitor_dashpro_sentry_recent_issues_critical',
        title: 'DashPro Sentry critical',
        status: 'open',
        workspace_id: 'workspace_dashpro',
      },
      {
        signal_id: 'signal_monitor_axon_watch_critical',
        title: 'Axon Watch critical',
        status: 'open',
        workspace_id: 'workspace_axon_watch',
      },
    ];

    expect(countActionableOpenSignals(items, 'workspace_dashpro')).toBe(1);
    expect(countActionableOpenSignals(items)).toBe(2);
  });

  it('prefers loaded inbox counts over stale runtime summary values', () => {
    expect(
      resolveOperatorSignalCount({
        inboxItems: [
          {
            signal_id: 'signal_monitor_dashpro_sentry_recent_issues_critical',
            title: 'DashPro Sentry critical',
            status: 'open',
          },
        ],
        inboxLoadState: 'loaded',
        runtimeSummaryOpenCount: 0,
      }),
    ).toBe(1);

    expect(
      resolveOperatorSignalCount({
        inboxItems: [],
        inboxLoadState: 'loading',
        runtimeSummaryOpenCount: 2,
      }),
    ).toBe(2);
  });

  it('keeps unscoped monitor signals visible in workspace counts', () => {
    expect(
      filterActionableOpenSignals(
        [
          {
            signal_id: 'signal_monitor_dashpro_sentry_recent_issues_critical',
            title: 'DashPro Sentry critical',
            status: 'open',
            workspace_id: '',
          },
        ],
        'workspace_dashpro',
      ),
    ).toHaveLength(1);
  });
});
