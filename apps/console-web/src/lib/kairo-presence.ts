export type KairoPresenceState =
  | 'idle'
  | 'observing'
  | 'listening'
  | 'speaking'
  | 'paused'
  | 'alerting'
  | 'privacy_blocked';

export function resolveKairoPresenceState(input: {
  privacyBlocked?: boolean;
  pendingApprovals: number;
  criticalSignals: number;
  highSignals: number;
  watchConnected: boolean;
  runtimeLoaded: boolean;
}): KairoPresenceState {
  if (input.privacyBlocked) {
    return 'privacy_blocked';
  }

  if (input.pendingApprovals > 0 || input.criticalSignals > 0 || input.highSignals > 0) {
    return 'alerting';
  }

  if (input.runtimeLoaded && input.watchConnected) {
    return 'observing';
  }

  return 'idle';
}

export function kairoPresenceLabel(state: KairoPresenceState): string {
  switch (state) {
    case 'observing':
      return 'KAIRO · observing';
    case 'listening':
      return 'KAIRO · listening';
    case 'speaking':
      return 'KAIRO · speaking';
    case 'paused':
      return 'KAIRO · paused';
    case 'alerting':
      return 'KAIRO · attention';
    case 'privacy_blocked':
      return 'KAIRO · muted';
    default:
      return 'KAIRO';
  }
}
