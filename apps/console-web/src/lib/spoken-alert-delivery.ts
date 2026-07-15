import type { SpokenAlertEligibility } from '../contracts/canonical';

import { speakKairoLine } from './kairo-voice-playback';
import type { KairoVoicePriority } from './kairo-voice-queue';
import { shouldSpeakAlert, spokenAlertDedupeKey } from './operator-presence';

export type SpokenAlertDeliveryChannel = 'voice_deck' | 'azure' | 'browser' | 'skipped';

export type VoiceDeckSpokenAlertHandler = (
  alert: SpokenAlertEligibility,
) => boolean | Promise<boolean>;

export type DeliverSpokenAlertOptions = {
  /** Default `alert`. Use `narration` for run milestones / live thinking. */
  priority?: KairoVoicePriority;
  /** Allow explicit triggers to speak even if a matching alert was already marked spoken. */
  dedupe?: boolean;
};

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
  options: DeliverSpokenAlertOptions = {},
): Promise<SpokenAlertDeliveryChannel> {
  if (options.dedupe !== false && !shouldSpeakAlert(alert, storage)) {
    return 'skipped';
  }

  if (voiceDeckSpokenAlertHandler && (options.priority ?? 'alert') === 'alert') {
    const handled = await voiceDeckSpokenAlertHandler(alert);
    if (handled) {
      return 'voice_deck';
    }
  }

  const result = await speakKairoLine(alert.message, {
    priority: options.priority ?? 'alert',
  });
  if (result.engine === 'azure') {
    return 'azure';
  }
  if (result.engine === 'browser') {
    return 'browser';
  }
  return 'skipped';
}

export { spokenAlertDedupeKey };
