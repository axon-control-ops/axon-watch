import { describe, expect, it } from 'vitest';

import { buildPersonaVoiceLineFallback } from './persona-voice-line';

describe('buildPersonaVoiceLineFallback', () => {
  it('names the live signal in plain English instead of asking which workspace to focus', () => {
    const line = buildPersonaVoiceLineFallback({
      pendingApprovals: 0,
      topSignalTitle: 'DashPro Sentry critical',
      topSignalWorkspaceId: 'workspace_dashpro',
      topSignalSummary: 'Sentry returned 5 unresolved issues',
      topSignalMeta: {
        signal_family: 'child_project_monitor',
        workspace_label: 'DashPro',
        monitor_status: 'critical',
      },
    });

    expect(line).toContain('DashPro');
    expect(line).not.toContain('Tell me which workspace to focus');
    expect(line).not.toContain('Top signal');
  });

  it('keeps approval priority above signals', () => {
    const line = buildPersonaVoiceLineFallback({
      pendingApprovals: 2,
      topSignalTitle: 'DashPro Sentry critical',
    });

    expect(line.toLowerCase()).toContain('yes or no');
    expect(line).toContain('2 jobs');
    expect(line).not.toContain('DashPro Sentry');
  });
});
