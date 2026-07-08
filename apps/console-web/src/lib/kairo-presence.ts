import { OPERATOR_PERSONA_NAME, personaStatusLabel } from './operator-persona-name';

export type KairoPresenceState =
  | 'idle'
  | 'observing'
  | 'listening'
  | 'speaking'
  | 'thinking'
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

export function kairoPresenceSubtitle(state: KairoPresenceState): string {
  switch (state) {
    case 'observing':
      return 'observing';
    case 'listening':
      return 'listening';
    case 'speaking':
      return 'speaking';
    case 'thinking':
      return 'checking';
    case 'paused':
      return 'paused';
    case 'alerting':
      return 'attention';
    case 'privacy_blocked':
      return 'muted';
    default:
      return 'standby';
  }
}

export function kairoPresenceLabel(state: KairoPresenceState): string {
  switch (state) {
    case 'observing':
      return personaStatusLabel('observing');
    case 'listening':
      return personaStatusLabel('listening');
    case 'speaking':
      return personaStatusLabel('speaking');
    case 'thinking':
      return personaStatusLabel('checking');
    case 'paused':
      return personaStatusLabel('paused');
    case 'alerting':
      return personaStatusLabel('attention');
    case 'privacy_blocked':
      return personaStatusLabel('muted');
    default:
      return OPERATOR_PERSONA_NAME;
  }
}
