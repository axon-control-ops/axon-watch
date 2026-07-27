import { describe, expect, it } from 'vitest';

import {
  ideDisplayKairoState,
  ideShowKairoSidebarExpanded,
  ideShowWatchInStatusBar,
  ideUseKairoChip,
  resolveIdeKairoChipState,
  resolveIdePresenceProfile,
  shouldSurfaceIdeEmployeeFailure,
} from './ide-presence-profile';

describe('ide presence profile', () => {
  it('defaults to quiet when watch is healthy and nothing is blocked', () => {
    expect(
      resolveIdePresenceProfile({
        pendingApprovals: 0,
        criticalSignals: 0,
        highSignals: 0,
        watchConnected: true,
        degradedActive: false,
        primaryRunPhase: 'executing',
      }),
    ).toBe('quiet');
  });

  it('promotes to interrupt when approvals or watch health fail', () => {
    expect(
      resolveIdePresenceProfile({
        pendingApprovals: 1,
        criticalSignals: 0,
        highSignals: 0,
        watchConnected: true,
        degradedActive: false,
        primaryRunPhase: 'executing',
      }),
    ).toBe('interrupt');

    expect(
      resolveIdePresenceProfile({
        pendingApprovals: 0,
        criticalSignals: 0,
        highSignals: 0,
        watchConnected: false,
        degradedActive: false,
        primaryRunPhase: 'executing',
      }),
    ).toBe('interrupt');
  });

  it('hides watch chip in IDE quiet tier when watch is healthy', () => {
    expect(
      ideShowWatchInStatusBar({
        layoutMode: 'ide',
        profile: 'quiet',
        watchConnected: true,
        degradedActive: false,
      }),
    ).toBe(false);
  });

  it('shows watch chip in IDE interrupt tier', () => {
    expect(
      ideShowWatchInStatusBar({
        layoutMode: 'ide',
        profile: 'interrupt',
        watchConnected: true,
        degradedActive: false,
      }),
    ).toBe(true);
  });

  it('uses compact KAIRO chip in quiet and assist tiers', () => {
    expect(ideUseKairoChip('quiet')).toBe(true);
    expect(ideUseKairoChip('assist')).toBe(true);
    expect(ideUseKairoChip('interrupt')).toBe(false);
  });

  it('maps observing to idle display in quiet tier', () => {
    expect(ideDisplayKairoState('quiet', 'observing')).toBe('idle');
    expect(ideDisplayKairoState('interrupt', 'observing')).toBe('observing');
  });

  it('keeps sidebar expanded only on interrupt or voice', () => {
    expect(ideShowKairoSidebarExpanded('quiet')).toBe(false);
    expect(ideShowKairoSidebarExpanded('interrupt')).toBe(true);
  });

  it('promotes idle chip to alerting when the active teammate thread failed', () => {
    expect(
      resolveIdeKairoChipState({
        profileState: 'idle',
        employeeFailureLine: 'Last job failed: npm test exited 1',
        agentStreamActive: false,
        kairoSpeechActive: false,
      }),
    ).toBe('alerting');
  });

  it('keeps chip idle while agent stream or speech is active', () => {
    expect(
      resolveIdeKairoChipState({
        profileState: 'idle',
        employeeFailureLine: 'Last job failed: npm test exited 1',
        agentStreamActive: true,
        kairoSpeechActive: false,
      }),
    ).toBe('idle');

    expect(
      resolveIdeKairoChipState({
        profileState: 'idle',
        employeeFailureLine: 'Last job failed: npm test exited 1',
        agentStreamActive: false,
        kairoSpeechActive: true,
      }),
    ).toBe('idle');
  });

  it('gates composer failure chrome on the same alerting rules as the Kairo chip', () => {
    const failureInput = {
      profileState: 'idle' as const,
      employeeFailureLine: 'Last job failed: npm test exited 1',
      agentStreamActive: false,
      kairoSpeechActive: false,
    };
    expect(shouldSurfaceIdeEmployeeFailure(failureInput)).toBe(true);
    expect(
      shouldSurfaceIdeEmployeeFailure({
        ...failureInput,
        agentStreamActive: true,
      }),
    ).toBe(false);
    expect(
      shouldSurfaceIdeEmployeeFailure({
        ...failureInput,
        employeeFailureLine: null,
      }),
    ).toBe(false);
    expect(
      shouldSurfaceIdeEmployeeFailure({
        ...failureInput,
        profileState: 'thinking',
      }),
    ).toBe(false);
  });
});
