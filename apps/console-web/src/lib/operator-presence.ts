import type { OperatorPresence, SpokenAlertEligibility } from '../contracts/canonical';

const SPOKEN_ALERT_DEDUPE_KEY = 'axon-x-spoken-alert:last';

export function shouldUseMobileCompactLayout(
  viewportWidth: number,
  presence: OperatorPresence | null | undefined,
): boolean {
  if (!presence?.mobile.foreground_only) {
    return false;
  }
  if (presence.mobile.compact_layout) {
    return true;
  }
  return viewportWidth > 0 && viewportWidth < 768 && presence.settings.mobile_compact_preferred;
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
  if (!shouldSpeakAlert(alert, storage)) {
    return false;
  }
  speakAlertMessage(alert.message, speech);
  return true;
}
