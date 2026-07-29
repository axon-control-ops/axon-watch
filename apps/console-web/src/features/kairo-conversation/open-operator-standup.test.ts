import { beforeEach, describe, expect, it, vi } from 'vitest';

const { navigateToAppSurface, submitKairoConversationTranscript } = vi.hoisted(() => ({
  navigateToAppSurface: vi.fn(),
  submitKairoConversationTranscript: vi.fn(async () => 'submitted' as const),
}));

vi.mock('../../lib/app-surface-route', () => ({
  navigateToAppSurface,
}));

vi.mock('./kairo-conversation-bus', () => ({
  submitKairoConversationTranscript,
}));

vi.mock('../report-theater/report-theater-state', () => ({
  reportTheaterOpen: { value: false },
}));

import { openOperatorStandup } from './open-operator-standup';

describe('openOperatorStandup', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns to console and submits REPORT', async () => {
    const setLayoutMode = vi.fn();
    await openOperatorStandup({ layoutMode: 'ide', setLayoutMode });
    expect(navigateToAppSurface).toHaveBeenCalledWith('console');
    expect(setLayoutMode).toHaveBeenCalledWith('operator');
    expect(submitKairoConversationTranscript).toHaveBeenCalledWith('REPORT');
  });
});
