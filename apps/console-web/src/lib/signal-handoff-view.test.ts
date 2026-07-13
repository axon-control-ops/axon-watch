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

  it('builds email-aware handoff task text', () => {
    expect(
      buildSignalHandoffTask({
        signal_id: 'signal_email_stub_urgent',
        title: 'Email needs follow-up: Urgent: DashPro deploy failed',
        summary: 'CTO — Respond to the blocker.',
        meta: {
          signal_family: 'email_triage',
          sender: 'CTO <cto@example.com>',
          subject: 'Urgent: DashPro deploy failed',
          recommended_action: 'reply_or_investigate',
          recommended_detail: 'Respond to the blocker or investigate the issue.',
        },
      }),
    ).toContain('Triage email from CTO <cto@example.com>');
  });

  it('resolves DashPro email handoff from operator workspace', () => {
    const resolved = resolveSignalHandoff(
      {
        signal_id: 'signal_email_stub_urgent',
        workspace_id: 'workspace_dashpro',
        title: 'Email needs follow-up: Urgent: DashPro deploy failed',
        summary: 'CTO — Respond to the blocker.',
        meta: {
          signal_family: 'email_triage',
          sender: 'CTO <cto@example.com>',
          subject: 'Urgent: DashPro deploy failed',
          recommended_action: 'reply_or_investigate',
          recommended_detail: 'Respond to the blocker or investigate the issue.',
        },
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
    expect(resolved?.task).toContain('Triage email from CTO <cto@example.com>');
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
