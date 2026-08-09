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

const SPOKEN_ALERT_DEDUPE_KEY = 'axon-x-spoken-alert:recent';
const SPOKEN_ALERT_DEDUPE_MAX = 24;
const SPOKEN_ALERT_DEDUPE_TTL_MS = 6 * 60 * 60 * 1000;

type SpokenAlertDedupeEntry = {
  key: string;
  spokenAt: number;
};

export function shouldUseMobileCompactLayout(
  viewportWidth: number,
  presence: OperatorPresence | null | undefined,
): boolean {
  return shouldUseMobileCompactLayoutFromViewport(viewportWidth, presence);
}

function defaultSpokenAlertStorage(): Pick<Storage, 'getItem' | 'setItem'> {
  try {
    if (typeof localStorage !== 'undefined') {
      return localStorage;
    }
  } catch {
    /* private mode */
  }
  try {
    if (typeof sessionStorage !== 'undefined') {
      return sessionStorage;
    }
  } catch {
    /* ignore */
  }
  return {
    getItem: () => null,
    setItem: () => undefined,
  };
}

function readSpokenAlertDedupeEntries(
  storage: Pick<Storage, 'getItem' | 'setItem'>,
): SpokenAlertDedupeEntry[] {
  const raw = storage.getItem(SPOKEN_ALERT_DEDUPE_KEY);
  if (!raw) {
    // Migrate the previous single-key format.
    const legacy = storage.getItem('axon-x-spoken-alert:last');
    return legacy ? [{ key: legacy, spokenAt: Date.now() }] : [];
  }
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed
      .map((entry) => {
        if (!entry || typeof entry !== 'object') {
          return null;
        }
        const record = entry as Partial<SpokenAlertDedupeEntry>;
        if (typeof record.key !== 'string' || typeof record.spokenAt !== 'number') {
          return null;
        }
        return { key: record.key, spokenAt: record.spokenAt };
      })
      .filter((entry): entry is SpokenAlertDedupeEntry => Boolean(entry));
  } catch {
    return [];
  }
}

export function spokenAlertDedupeKey(alert: SpokenAlertEligibility): string {
  return alert.signal_id ?? alert.reason;
}

export function shouldSpeakAlert(
  alert: SpokenAlertEligibility,
  storage: Pick<Storage, 'getItem' | 'setItem'> = defaultSpokenAlertStorage(),
): boolean {
  if (!alert.eligible || !alert.message.trim()) {
    return false;
  }
  const key = spokenAlertDedupeKey(alert);
  const now = Date.now();
  const recent = readSpokenAlertDedupeEntries(storage).filter(
    (entry) => now - entry.spokenAt <= SPOKEN_ALERT_DEDUPE_TTL_MS,
  );
  if (recent.some((entry) => entry.key === key)) {
    return false;
  }
  const next = [...recent.filter((entry) => entry.key !== key), { key, spokenAt: now }].slice(
    -SPOKEN_ALERT_DEDUPE_MAX,
  );
  storage.setItem(SPOKEN_ALERT_DEDUPE_KEY, JSON.stringify(next));
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
  storage: Pick<Storage, 'getItem' | 'setItem'> = defaultSpokenAlertStorage(),
): Promise<boolean> {
  return (await deliverSpokenOperatorAlert(alert, storage)) !== 'skipped';
}
