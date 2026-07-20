import type { RunRecord } from '../contracts/canonical';

import type { KairoPresenceState } from './kairo-presence';
import type { RuntimeStripChip } from './runtime-strip';

export type IdePresenceProfile = 'quiet' | 'assist' | 'interrupt' | 'voice';

export function resolveIdePresenceProfile(input: {
  pendingApprovals: number;
  criticalSignals: number;
  highSignals: number;
  watchConnected: boolean;
  degradedActive: boolean;
  primaryRunPhase: RunRecord['phase'] | null | undefined;
  agentStreamActive?: boolean;
  voiceSessionActive?: boolean;
}): IdePresenceProfile {
  if (input.voiceSessionActive) {
    return 'voice';
  }

  if (input.pendingApprovals > 0) {
    return 'interrupt';
  }

  if (input.criticalSignals > 0 || input.highSignals > 0) {
    return 'interrupt';
  }

  if (!input.watchConnected || input.degradedActive) {
    return 'interrupt';
  }

  if (input.primaryRunPhase === 'awaiting_approval') {
    return 'interrupt';
  }

  if (input.agentStreamActive) {
    return 'assist';
  }

  return 'quiet';
}

export function ideShowWatchInStatusBar(input: {
  layoutMode: 'operator' | 'ide';
  profile: IdePresenceProfile;
  watchConnected: boolean;
  degradedActive: boolean;
}): boolean {
  if (input.layoutMode !== 'ide') {
    return true;
  }

  if (input.profile === 'interrupt') {
    return true;
  }

  return !input.watchConnected || input.degradedActive;
}

export function ideUseKairoChip(profile: IdePresenceProfile): boolean {
  return profile === 'quiet' || profile === 'assist';
}

export function ideDisplayKairoState(
  profile: IdePresenceProfile,
  state: KairoPresenceState,
): KairoPresenceState {
  if (profile === 'quiet' && (state === 'observing' || state === 'idle')) {
    return 'idle';
  }

  return state;
}

/** Surface a failed teammate shift on the compact Kairo chip when nothing else is live. */
export function resolveIdeKairoChipState(input: {
  profileState: KairoPresenceState;
  employeeFailureLine: string | null;
  agentStreamActive: boolean;
  kairoSpeechActive: boolean;
}): KairoPresenceState {
  if (
    input.employeeFailureLine &&
    !input.agentStreamActive &&
    !input.kairoSpeechActive &&
    input.profileState === 'idle'
  ) {
    return 'alerting';
  }

  return input.profileState;
}

/** Composer dock, sidebar, and footer share this gate for failure chrome. */
export function shouldSurfaceIdeEmployeeFailure(input: {
  profileState: KairoPresenceState;
  employeeFailureLine: string | null;
  agentStreamActive: boolean;
  kairoSpeechActive: boolean;
}): boolean {
  return resolveIdeKairoChipState(input) === 'alerting';
}

export function ideShowKairoSidebarExpanded(profile: IdePresenceProfile): boolean {
  return profile === 'interrupt' || profile === 'voice';
}

export function filterTopbarChipsForIde(
  chips: RuntimeStripChip[],
  layoutMode: 'operator' | 'ide',
  profile: IdePresenceProfile,
): RuntimeStripChip[] {
  if (layoutMode !== 'ide' || profile === 'interrupt' || profile === 'voice') {
    return chips;
  }

  return chips.filter((chip) => chip.id !== 'watch');
}
