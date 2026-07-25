import type { OperatorPresence, SpokenAlertEligibility } from '../../contracts/canonical';

export type VoiceCockpitPresenceState =
  | 'idle'
  | 'observing'
  | 'alerting'
  | 'privacy_blocked';

export function voiceCockpitPresenceState(
  presence: OperatorPresence | null | undefined,
): VoiceCockpitPresenceState {
  if (!presence) {
    return 'idle';
  }
  return presence.presence_state;
}

export function voiceCockpitStatusLine(presence: OperatorPresence | null | undefined): string {
  if (!presence) {
    return 'Voice cockpit ready';
  }
  const line = presence.persona_voice_line?.trim();
  if (line) {
    return line;
  }
  if (presence.presence_state === 'privacy_blocked') {
    return 'Privacy mode — voice alerts muted';
  }
  return 'Foreground voice cockpit';
}

export function shouldReactToBriefingSpokenAlert(
  alert: SpokenAlertEligibility | null | undefined,
): alert is SpokenAlertEligibility {
  return Boolean(alert?.eligible && alert.message.trim());
}

export function spokenAlertSignature(alert: SpokenAlertEligibility): string {
  return `${alert.reason}:${alert.signal_id ?? ''}:${alert.message.trim()}`;
}
