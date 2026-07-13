import { describe, expect, it } from 'vitest';

import {
  buildSignalHandoffTask,
  canHandoffSignalToIde,
  resolveSignalHandoff,
} from './signal-handoff-view';

describe('signal-handoff-view', () => {
  it('blocks bootstrap signals from handoff', () => {
    expect(
      canHandoffSignalToIde({
        signal_id: 'signal_watch_bootstrap_ready',
        title: 'Watch bootstrap ready',
      }),
    ).toBe(false);
  });

  it('uses an explicit task when provided', () => {
    expect(
      buildSignalHandoffTask({
        signal_id: 'signal_monitor_dashpro_sentry_recent_issues_warning',
        title: 'DashPro Sentry warning',
        summary: '3 unresolved issues',
        task: 'Investigate signal "DashPro Sentry warning": 3 unresolved issues',
      }),
    ).toBe('Investigate signal "DashPro Sentry warning": 3 unresolved issues');
  });

  it('resolves cross-workspace handoff', () => {
    const resolved = resolveSignalHandoff(
      {
        signal_id: 'signal_monitor_dashpro_sentry_recent_issues_warning',
        workspace_id: 'workspace_dashpro',
        title: 'DashPro Sentry warning',
        summary: '3 unresolved issues',
      },
      'workspace_axon_watch',
      [
        { workspace_id: 'workspace_axon_watch', display_name: 'Axon Watch' },
        { workspace_id: 'workspace_dashpro', display_name: 'DashPro' },
      ],
    );

    expect(resolved?.mode).toBe('handoff');
    expect(resolved?.sourceWorkspaceId).toBe('workspace_axon_watch');
    expect(resolved?.targetWorkspaceId).toBe('workspace_dashpro');
    expect(resolved?.task).toBe(
      'Investigate signal "DashPro Sentry warning": 3 unresolved issues',
    );
  });
});
