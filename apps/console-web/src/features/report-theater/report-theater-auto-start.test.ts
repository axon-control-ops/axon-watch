import { describe, expect, it } from 'vitest';

import {
  isReportTheaterAutoStartTransition,
  markReportTheaterAutoStarted,
  isReportTheaterAutoStartPending,
  REPORT_THEATER_AUTO_START_ENABLED,
  resetReportTheaterAutoStartForTests,
  shouldAutoStartReportTheater,
  shouldStartReportTheaterForBriefing,
} from './report-theater-auto-start';
import { resetReportTheaterStateForTests } from './report-theater-state';

describe('report-theater-auto-start', () => {
  it('keeps auto-start disabled so briefing polls never open Command Theater', () => {
    expect(REPORT_THEATER_AUTO_START_ENABLED).toBe(false);
    resetReportTheaterAutoStartForTests();
    resetReportTheaterStateForTests();
    expect(
      shouldAutoStartReportTheater({
        autonomyMode: 'full',
        privacyMode: false,
        spokenAlertsEnabled: true,
        pendingApprovals: 2,
        topSignalCount: 13,
        awaitingEngagementCount: 1,
        degradedActive: true,
        briefKey: 'signal-a',
        now: 1_000_000,
      }),
    ).toBe(false);
    expect(
      shouldStartReportTheaterForBriefing({
        autonomyMode: 'full',
        previousBriefKey: undefined,
        currentBriefKey: 'signal-a',
        eligible: true,
      }),
    ).toBe(false);
  });

  it('uses hydration as a quiet baseline and starts only after the briefing changes', () => {
    expect(isReportTheaterAutoStartTransition(undefined, 'signal-a', true)).toBe(false);
    expect(isReportTheaterAutoStartTransition('signal-a', 'signal-a', true)).toBe(false);
    expect(isReportTheaterAutoStartTransition('signal-a', 'signal-b', true)).toBe(true);
    expect(isReportTheaterAutoStartTransition('signal-a', 'signal-b', false)).toBe(false);
  });

  it('marks auto-start pending so passive advisories can yield to REPORT', () => {
    resetReportTheaterAutoStartForTests();
    expect(isReportTheaterAutoStartPending(1_000_000)).toBe(false);
    markReportTheaterAutoStarted('signal-a', 1_000_000);
    expect(isReportTheaterAutoStartPending(1_005_000)).toBe(true);
    expect(isReportTheaterAutoStartPending(1_030_000)).toBe(false);
  });

  it('stays quiet in manual mode', () => {
    resetReportTheaterAutoStartForTests();
    resetReportTheaterStateForTests();
    expect(
      shouldAutoStartReportTheater({
        autonomyMode: 'manual',
        privacyMode: false,
        spokenAlertsEnabled: true,
        pendingApprovals: 1,
        topSignalCount: 1,
        awaitingEngagementCount: 1,
        degradedActive: true,
        briefKey: 'x',
        now: 2_000_000,
      }),
    ).toBe(false);
  });
});
