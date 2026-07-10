import { describe, expect, it } from 'vitest';

import { buildPersonaVoiceLineFallback } from './persona-voice-line';

describe('buildPersonaVoiceLineFallback', () => {
  it('names the live signal instead of asking which workspace to focus', () => {
    const line = buildPersonaVoiceLineFallback({
      pendingApprovals: 0,
      topSignalTitle: 'DashPro Sentry critical',
      topSignalWorkspaceId: 'workspace_dashpro',
      topSignalSummary: 'Sentry returned 5 unresolved issues',
    });

    expect(line).toContain('DashPro Sentry critical');
    expect(line).toContain('dashpro');
    expect(line).not.toContain('Tell me which workspace to focus');
  });

  it('keeps approval priority above signals', () => {
    const line = buildPersonaVoiceLineFallback({
      pendingApprovals: 2,
      topSignalTitle: 'DashPro Sentry critical',
    });

    expect(line).toContain('2 approvals');
    expect(line).not.toContain('DashPro Sentry');
  });
});
