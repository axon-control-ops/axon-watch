import type { SpokenAlertEligibility } from '../contracts/canonical';

import { speakKairoLine } from './kairo-voice-playback';
import { shouldSpeakAlert, spokenAlertDedupeKey } from './operator-presence';

export type SpokenAlertDeliveryChannel = 'voice_deck' | 'azure' | 'browser' | 'skipped';

export type VoiceDeckSpokenAlertHandler = (
  alert: SpokenAlertEligibility,
) => boolean | Promise<boolean>;

let voiceDeckSpokenAlertHandler: VoiceDeckSpokenAlertHandler | null = null;

export function registerVoiceDeckSpokenAlertHandler(
  handler: VoiceDeckSpokenAlertHandler | null,
): void {
  voiceDeckSpokenAlertHandler = handler;
}

export function getVoiceDeckSpokenAlertHandler(): VoiceDeckSpokenAlertHandler | null {
  return voiceDeckSpokenAlertHandler;
}

export async function deliverSpokenOperatorAlert(
  alert: SpokenAlertEligibility,
  storage: Pick<Storage, 'getItem' | 'setItem'> = sessionStorage,
): Promise<SpokenAlertDeliveryChannel> {
  if (!shouldSpeakAlert(alert, storage)) {
    return 'skipped';
  }

  if (voiceDeckSpokenAlertHandler) {
    const handled = await voiceDeckSpokenAlertHandler(alert);
    if (handled) {
      return 'voice_deck';
    }
  }

  const result = await speakKairoLine(alert.message);
  if (result.engine === 'azure') {
    return 'azure';
  }
  if (result.engine === 'browser') {
    return 'browser';
  }
  return 'skipped';
}

export { spokenAlertDedupeKey };
