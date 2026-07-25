import type { OperatorPresence, SpokenAlertEligibility } from '../contracts/canonical';

import { deliverSpokenOperatorAlert } from './spoken-alert-delivery';
import { enqueueSpeech, type SpeechPort } from './speech-queue';

export type { SpeechPort } from './speech-queue';
export { enqueueSpeech, resetSpeechQueue } from './speech-queue';

export {
  deliverSpokenOperatorAlert,
  registerVoiceDeckSpokenAlertHandler,
  type SpokenAlertDeliveryChannel,
  type VoiceDeckSpokenAlertHandler,
} from './spoken-alert-delivery';

import {
  shouldUseMobileCompactLayout as shouldUseMobileCompactLayoutFromViewport,
} from './viewport-compact';

export { MOBILE_COMPACT_BREAKPOINT, shouldRequestViewportCompactBriefing } from './viewport-compact';

const SPOKEN_ALERT_DEDUPE_KEY = 'axon-x-spoken-alert:last';

export function shouldUseMobileCompactLayout(
  viewportWidth: number,
  presence: OperatorPresence | null | undefined,
): boolean {
  return shouldUseMobileCompactLayoutFromViewport(viewportWidth, presence);
}

export function spokenAlertDedupeKey(alert: SpokenAlertEligibility): string {
  return alert.signal_id ?? alert.reason;
}

export function shouldSpeakAlert(
  alert: SpokenAlertEligibility,
  storage: Pick<Storage, 'getItem' | 'setItem'> = sessionStorage,
): boolean {
  if (!alert.eligible || !alert.message.trim()) {
    return false;
  }
  const key = spokenAlertDedupeKey(alert);
  const last = storage.getItem(SPOKEN_ALERT_DEDUPE_KEY);
  if (last === key) {
    return false;
  }
  storage.setItem(SPOKEN_ALERT_DEDUPE_KEY, key);
  return true;
}

/** Legacy browser-only path — prefer deliverSpokenOperatorAlert / speakKairoLine. */
export function speakAlertMessage(message: string, speech: SpeechPort | null): void {
  if (!speech || !message.trim()) {
    return;
  }
  enqueueSpeech(message, speech);
}

export async function maybeSpeakOperatorAlert(
  alert: SpokenAlertEligibility,
  storage: Pick<Storage, 'getItem' | 'setItem'> = sessionStorage,
): Promise<boolean> {
  return (await deliverSpokenOperatorAlert(alert, storage)) !== 'skipped';
}
