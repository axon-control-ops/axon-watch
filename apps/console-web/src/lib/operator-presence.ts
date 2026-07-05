import type { OperatorPresence, SpokenAlertEligibility } from '../contracts/canonical';

import { deliverSpokenOperatorAlert } from './spoken-alert-delivery';

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

export function speakAlertMessage(message: string, speech: Pick<SpeechSynthesis, 'speak'> | null): void {
  if (
    !speech ||
    !message.trim() ||
    typeof SpeechSynthesisUtterance === 'undefined'
  ) {
    return;
  }
  const utterance = new SpeechSynthesisUtterance(message);
  utterance.rate = 1;
  speech.speak(utterance);
}

export function maybeSpeakOperatorAlert(
  alert: SpokenAlertEligibility,
  speech: Pick<SpeechSynthesis, 'speak'> | null = typeof speechSynthesis === 'undefined'
    ? null
    : speechSynthesis,
  storage: Pick<Storage, 'getItem' | 'setItem'> = sessionStorage,
): boolean {
  return deliverSpokenOperatorAlert(alert, speech, storage) !== 'skipped';
}
