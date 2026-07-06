import type { SpokenAlertEligibility } from '../../contracts/canonical';

import { speakAlertMessage, type SpeechPort } from '../../lib/operator-presence';
import { jarvisAlertSpeech } from '../../lib/kairo-voice-script';
import { registerVoiceDeckSpokenAlertHandler } from '../../lib/spoken-alert-delivery';

export function handleVoiceDeckSpokenAlert(
  alert: SpokenAlertEligibility,
  speech: SpeechPort | null = typeof speechSynthesis === 'undefined'
    ? null
    : speechSynthesis,
): boolean {
  if (!alert.eligible || !alert.message.trim()) {
    return false;
  }

  const line = jarvisAlertSpeech(alert.message);
  if (!line) {
    return false;
  }

  speakAlertMessage(line, speech);
  return true;
}

export function registerVoiceDeckOnBoot(
  speech: SpeechPort | null = typeof speechSynthesis === 'undefined'
    ? null
    : speechSynthesis,
): void {
  registerVoiceDeckSpokenAlertHandler((alert) => handleVoiceDeckSpokenAlert(alert, speech));
}
