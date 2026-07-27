import type { KairoVoiceSpeaker } from './kairo-voice-utterance';
import { OPERATOR_PERSONA_NAME } from './operator-persona-name';

/** Resolve who the left-rail agent chip should name while speech/activity is live. */
export function resolveIdePresencePersonaName(input: {
  speaker: KairoVoiceSpeaker | null | undefined;
  kairoSpeechActive: boolean;
  surfaceEmployeeFailure: boolean;
  activeEmployeeName: string | null | undefined;
  /** Kept after TTS ends so the chip does not snap back to VAXON. */
  stickySpeakerName?: string | null;
  stickyFollowupActive?: boolean;
}): string {
  const active = input.activeEmployeeName?.trim() || null;
  const employeeFromSpeaker =
    input.speaker?.kind === 'employee' ? input.speaker.name?.trim() || null : null;
  // Azure-voice-only stubs used to ship as "Teammate" — prefer the open teammate.
  if (employeeFromSpeaker && employeeFromSpeaker.toLowerCase() !== 'teammate') {
    return employeeFromSpeaker;
  }
  if (employeeFromSpeaker && active) {
    return active;
  }
  if (input.speaker?.kind === 'vaxon') {
    return OPERATOR_PERSONA_NAME;
  }
  const sticky = input.stickySpeakerName?.trim() || null;
  if (
    sticky &&
    sticky.toLowerCase() !== 'teammate' &&
    (input.kairoSpeechActive || input.stickyFollowupActive)
  ) {
    return sticky;
  }
  if (sticky && sticky.toLowerCase() === 'teammate' && active && input.stickyFollowupActive) {
    return active;
  }
  if (input.kairoSpeechActive) {
    if (active) {
      return active;
    }
    return OPERATOR_PERSONA_NAME;
  }
  if (input.surfaceEmployeeFailure) {
    if (active) {
      return active;
    }
  }
  return OPERATOR_PERSONA_NAME;
}
