import { describe, expect, it } from 'vitest';

import { buildOperatorIncidentFeed } from './operator-incident-feed-view';

describe('operator-incident-feed-view', () => {
  it('filters signals to active workspace', () => {
    const view = buildOperatorIncidentFeed({
      workspaceId: 'workspace_dashpro',
      topSignals: [
        {
          signal_id: 'sig_a',
          workspace_id: 'workspace_dashpro',
          title: 'Sentry spike',
          summary: 'Errors up 40%',
          severity: 'high',
          status: 'open',
          source: 'watch',
          created_at: '2026-07-07T19:55:00Z',
          updated_at: '2026-07-07T20:00:00Z',
          action_type: 'open_dashboard',
        },
        {
          signal_id: 'sig_b',
          workspace_id: 'workspace_axon_watch',
          title: 'Other workspace',
          summary: 'Ignore me',
          severity: 'info',
          status: 'open',
          source: 'watch',
          created_at: '2026-07-07T19:55:00Z',
          updated_at: '2026-07-07T20:00:00Z',
          action_type: 'open_dashboard',
        },
      ],
      fleetHealth: null,
    });

    expect(view.items).toHaveLength(1);
    expect(view.items[0]?.title).toBe('Sentry spike');
    expect(view.items[0]?.plainWhat).toBeTruthy();
    expect(view.items[0]?.plainWhat.toLowerCase()).toContain('look');
    expect(view.items[0]?.plainYouDo).toBeTruthy();
    expect(view.items[0]?.plainAgentDo).toBeTruthy();
  });

  it('dedupes twin signals that share the same title', () => {
    const view = buildOperatorIncidentFeed({
      workspaceId: 'workspace_dashpro',
      topSignals: [
        {
          signal_id: 'sig_android_a',
          workspace_id: 'workspace_dashpro',
          title: 'Android CI/CD Pipeline failed on feat/self-hosted-ci-runner',
          summary: 'Workflow failed',
          severity: 'critical',
          status: 'open',
          source: 'watch',
          created_at: '2026-07-07T19:55:00Z',
          updated_at: '2026-07-07T20:00:00Z',
          action_type: 'open_dashboard',
        },
        {
          signal_id: 'sig_android_b',
          workspace_id: 'workspace_dashpro',
          title: 'Android CI/CD Pipeline failed on feat/self-hosted-ci-runner',
          summary: 'Workflow failed again',
          severity: 'critical',
          status: 'open',
          source: 'watch',
          created_at: '2026-07-07T19:56:00Z',
          updated_at: '2026-07-07T20:01:00Z',
          action_type: 'open_dashboard',
        },
      ],
      fleetHealth: null,
    });

    expect(view.items).toHaveLength(1);
    expect(view.items[0]?.id).toBe('sig_android_a');
  });

  it('prefers matching server explanation for plainWhat', () => {
    const view = buildOperatorIncidentFeed({
      workspaceId: 'workspace_dashpro',
      topSignals: [
        {
          signal_id: 'sig_a',
          workspace_id: 'workspace_dashpro',
          title: 'Sentry spike',
          summary: 'Errors up 40%',
          severity: 'high',
          status: 'open',
          source: 'watch',
          created_at: '2026-07-07T19:55:00Z',
          updated_at: '2026-07-07T20:00:00Z',
          action_type: 'open_dashboard',
        },
      ],
      fleetHealth: null,
      serverSignalId: 'sig_a',
      serverReason: 'high_urgency_signal',
      serverExplanation: {
        what: 'Server plain English for Sentry.',
        you_do: 'Open Attention.',
        agent_do: 'Investigate Sentry.',
        spoken: 'Sentry needs a look.',
      },
    });

    expect(view.items[0]?.plainWhat).toBe('Server plain English for Sentry.');
    expect(view.items[0]?.plainYouDo).toBe('Open Attention.');
    expect(view.items[0]?.plainAgentDo).toBe('Investigate Sentry.');
  });
});
