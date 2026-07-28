import { describe, expect, it } from 'vitest';

import {
  isReportTheaterAutoStartTransition,
  markReportTheaterAutoStarted,
  isReportTheaterAutoStartPending,
  resetReportTheaterAutoStartForTests,
  shouldAutoStartReportTheater,
  shouldStartReportTheaterForBriefing,
} from './report-theater-auto-start';
import { resetReportTheaterStateForTests } from './report-theater-state';

describe('report-theater-auto-start', () => {
  it('uses hydration as a quiet baseline and starts only after the briefing changes', () => {
    expect(isReportTheaterAutoStartTransition(undefined, 'signal-a', true)).toBe(false);
    expect(isReportTheaterAutoStartTransition('signal-a', 'signal-a', true)).toBe(false);
    expect(isReportTheaterAutoStartTransition('signal-a', 'signal-b', true)).toBe(true);
    expect(isReportTheaterAutoStartTransition('signal-a', 'signal-b', false)).toBe(false);
  });

  it('lets Full Autonomous start on the first actionable briefing', () => {
    expect(
      shouldStartReportTheaterForBriefing({
        autonomyMode: 'full',
        previousBriefKey: undefined,
        currentBriefKey: 'signal-a',
        eligible: true,
      }),
    ).toBe(true);
    expect(
      shouldStartReportTheaterForBriefing({
        autonomyMode: 'semi',
        previousBriefKey: undefined,
        currentBriefKey: 'signal-a',
        eligible: true,
      }),
    ).toBe(false);
    expect(
      shouldStartReportTheaterForBriefing({
        autonomyMode: 'semi',
        previousBriefKey: 'signal-a',
        currentBriefKey: 'signal-b',
        eligible: true,
      }),
    ).toBe(true);
    expect(
      shouldStartReportTheaterForBriefing({
        autonomyMode: 'full',
        previousBriefKey: undefined,
        currentBriefKey: 'signal-a',
        eligible: false,
      }),
    ).toBe(false);
  });

  it('marks auto-start pending so passive advisories can yield to REPORT', () => {
    resetReportTheaterAutoStartForTests();
    expect(isReportTheaterAutoStartPending(1_000_000)).toBe(false);
    markReportTheaterAutoStarted('signal-a', 1_000_000);
    expect(isReportTheaterAutoStartPending(1_005_000)).toBe(true);
    expect(isReportTheaterAutoStartPending(1_030_000)).toBe(false);
  });

  it('starts in semi/full when actionable and cools down repeats', () => {
    resetReportTheaterAutoStartForTests();
    resetReportTheaterStateForTests();
    const base = {
      autonomyMode: 'semi' as const,
      privacyMode: false,
      spokenAlertsEnabled: true,
      pendingApprovals: 0,
      topSignalCount: 2,
      awaitingEngagementCount: 0,
      degradedActive: false,
      briefKey: 'signal-a',
      now: 1_000_000,
    };
    expect(shouldAutoStartReportTheater(base)).toBe(true);
    markReportTheaterAutoStarted(base.briefKey, base.now);
    expect(shouldAutoStartReportTheater({ ...base, now: 1_020_000 })).toBe(false);
    expect(
      shouldAutoStartReportTheater({
        ...base,
        briefKey: 'signal-b',
        now: 1_000_000 + 50_000,
      }),
    ).toBe(true);
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
