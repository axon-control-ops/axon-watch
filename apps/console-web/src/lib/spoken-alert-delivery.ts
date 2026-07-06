import type { SpokenAlertEligibility } from '../contracts/canonical';

import { shouldSpeakAlert, speakAlertMessage, spokenAlertDedupeKey } from './operator-presence';
import type { SpeechPort } from './speech-queue';

export type SpokenAlertDeliveryChannel = 'voice_deck' | 'browser_tts' | 'skipped';

export type VoiceDeckSpokenAlertHandler = (alert: SpokenAlertEligibility) => boolean;

let voiceDeckSpokenAlertHandler: VoiceDeckSpokenAlertHandler | null = null;

export function registerVoiceDeckSpokenAlertHandler(
  handler: VoiceDeckSpokenAlertHandler | null,
): void {
  voiceDeckSpokenAlertHandler = handler;
}

export function getVoiceDeckSpokenAlertHandler(): VoiceDeckSpokenAlertHandler | null {
  return voiceDeckSpokenAlertHandler;
}

export function deliverSpokenOperatorAlert(
  alert: SpokenAlertEligibility,
  speech: SpeechPort | null = typeof speechSynthesis === 'undefined'
    ? null
    : speechSynthesis,
  storage: Pick<Storage, 'getItem' | 'setItem'> = sessionStorage,
): SpokenAlertDeliveryChannel {
  if (!shouldSpeakAlert(alert, storage)) {
    return 'skipped';
  }

  if (voiceDeckSpokenAlertHandler?.(alert)) {
    return 'voice_deck';
  }

  speakAlertMessage(alert.message, speech);
  return 'browser_tts';
}

export { spokenAlertDedupeKey };
