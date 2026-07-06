import type { SpokenAlertEligibility } from '../../contracts/canonical';

import { speakAlertMessage, type SpeechPort } from '../../lib/operator-presence';
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

  speakAlertMessage(alert.message.trim(), speech);
  return true;
}

export function registerVoiceDeckOnBoot(
  speech: SpeechPort | null = typeof speechSynthesis === 'undefined'
    ? null
    : speechSynthesis,
): void {
  registerVoiceDeckSpokenAlertHandler((alert) => handleVoiceDeckSpokenAlert(alert, speech));
}
