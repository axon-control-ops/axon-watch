import { describe, expect, it } from 'vitest';

import {
  explainOperatorAlert,
  isBootstrapSummarySignal,
  lastResortSpokenInvite,
  signalOperatorHint,
  watchRuleTooltip,
} from './operator-signal-hints';

describe('operator-signal-hints', () => {
  it('detects bootstrap summary signals', () => {
    expect(
      isBootstrapSummarySignal('signal_runtime_summary_degraded', 'Bootstrap: runtime summary stale'),
    ).toBe(true);
    expect(
      isBootstrapSummarySignal('signal_watch_bootstrap_ready', 'Watch bootstrap ready'),
    ).toBe(true);
  });

  it('returns bootstrap layman copy', () => {
    const explained = explainOperatorAlert({
      signalId: 'signal_runtime_summary_degraded',
      title: 'Bootstrap: runtime summary stale',
    });
    expect(explained.what).toContain('warming up');
    expect(explained.youDo).toContain('ignore');
    expect(explained.agentDo).toContain('not treat this as an incident');
    expect(signalOperatorHint({
      signalId: 'signal_runtime_summary_degraded',
      title: 'Bootstrap: runtime summary stale',
    })).toContain('What happened:');
  });

  it('returns child-project monitor hint with vault guidance', () => {
    const explained = explainOperatorAlert({
      signalId: 'signal_monitor_dashpro_sentry_recent_issues_warning',
      title: 'DashPro Sentry warning',
      meta: {
        signal_family: 'child_project_monitor',
        workspace_label: 'DashPro',
        monitor_status: 'warning',
      },
    });
    expect(explained.what).toContain('DashPro');
    expect(explained.youDo).toContain('Vault');
    expect(explained.agentDo).toContain('Investigate the DashPro monitor');
  });

  it('returns email triage hint copy', () => {
    const explained = explainOperatorAlert({
      signalId: 'signal_email_stub_urgent',
      title: 'Email needs follow-up: Urgent deploy',
      meta: {
        signal_family: 'email_triage',
        sender: 'CTO <cto@example.com>',
        recommended_action: 'reply_or_investigate',
      },
    });
    expect(explained.what).toContain('An email from CTO');
    expect(explained.spoken).toContain('CTO');
  });

  it('explains approvals in plain English', () => {
    const explained = explainOperatorAlert({ pendingApprovals: 2 });
    expect(explained.what).toContain('2 agent jobs');
    expect(explained.youDo).toContain('Approve');
    expect(explained.agentDo).toContain('Do not continue until the operator approves');
    expect(explained.spoken).toContain('yes or no');
    expect(explained.spoken).toContain('Approve or reject');
  });

  it('explains connector failures without jargon-only copy', () => {
    const explained = explainOperatorAlert({
      signalId: 'signal_connector_console_web_unavailable',
      title: 'Console web connector unavailable',
    });
    expect(explained.what.toLowerCase()).toContain('connection');
    expect(explained.youDo.toLowerCase()).toMatch(/service|vault/);
    expect(explained.agentDo.toLowerCase()).toContain('diagnose');
  });

  it('explains observe mode is not a button', () => {
    expect(watchRuleTooltip('observe')).toContain('only watching');
  });

  it('prefers Attention invites over dig-in for unknown alerts', () => {
    expect(lastResortSpokenInvite('DashPro Sentry critical')).toBe(
      'Open Attention for DashPro Sentry critical?',
    );
    expect(lastResortSpokenInvite('')).toBe('Want me to open Attention?');
    expect(lastResortSpokenInvite('')).not.toMatch(/shall i dig in/i);
    const explained = explainOperatorAlert({
      signalId: 'signal_unknown_widget_anomaly',
      title: 'Odd widget anomaly',
      summary: 'Something unusual happened in a widget.',
    });
    expect(explained.spoken).toContain('Open Attention for Odd widget anomaly?');
    expect(explained.spoken.toLowerCase()).not.toContain('shall i dig in');
  });
});

