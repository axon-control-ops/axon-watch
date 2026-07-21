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
  });
});
