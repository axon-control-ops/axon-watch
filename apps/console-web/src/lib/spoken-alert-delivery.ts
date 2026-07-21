import { readonly, ref } from 'vue';

import type { SpokenAlertEligibility } from '../contracts/canonical';

import {
  isKairoMediaUnlocked,
  onKairoAudioUnlocked,
} from './kairo-audio-unlock';
import { scheduleKairoVoiceFollowupWindowAfterSpeech } from './kairo-voice-followup-window';
import { speakKairoLine } from './kairo-voice-playback';
import type { KairoVoicePriority } from './kairo-voice-queue';
import { shouldSpeakAlert, spokenAlertDedupeKey } from './operator-presence';

export type SpokenAlertDeliveryChannel =
  | 'voice_deck'
  | 'azure'
  | 'browser'
  | 'queued'
  | 'skipped';

export type VoiceDeckSpokenAlertHandler = (
  alert: SpokenAlertEligibility,
) => boolean | Promise<boolean>;

export type DeliverSpokenAlertOptions = {
  /** Default `alert`. Use `narration` for run milestones / live thinking. */
  priority?: KairoVoicePriority;
  /** Allow explicit triggers to speak even if a matching alert was already marked spoken. */
  dedupe?: boolean;
  /** Prefer employee neural voice when narrating an employee IDE thread. */
  azureVoiceId?: string | null;
  /**
   * When true (default for `alert` priority), hold delivery until media unlock
   * so we do not drop the line or surprise with unlabeled robotic TTS.
   */
  queueUntilUnlock?: boolean;
  /** Open the post-speech follow-up listen window (default true for alerts). */
  openFollowupWindow?: boolean;
};

type QueuedSpokenAlert = {
  alert: SpokenAlertEligibility;
  storage: Pick<Storage, 'getItem' | 'setItem'>;
  options: DeliverSpokenAlertOptions;
};

let voiceDeckSpokenAlertHandler: VoiceDeckSpokenAlertHandler | null = null;
let pendingUntilUnlock: QueuedSpokenAlert[] = [];
let unlockFlushInstalled = false;
const pendingQueueSize = ref(0);

export const spokenAlertPendingQueueSize = readonly(pendingQueueSize);

function syncQueueSize(): void {
  pendingQueueSize.value = pendingUntilUnlock.length;
}

export function registerVoiceDeckSpokenAlertHandler(
  handler: VoiceDeckSpokenAlertHandler | null,
): void {
  voiceDeckSpokenAlertHandler = handler;
}

export function getVoiceDeckSpokenAlertHandler(): VoiceDeckSpokenAlertHandler | null {
  return voiceDeckSpokenAlertHandler;
}

function ensureUnlockFlushListener(): void {
  if (unlockFlushInstalled || typeof window === 'undefined') {
    return;
  }
  unlockFlushInstalled = true;
  onKairoAudioUnlocked(() => {
    void flushQueuedSpokenAlerts();
  });
}

function shouldQueueUntilUnlock(options: DeliverSpokenAlertOptions): boolean {
  if (options.queueUntilUnlock === false) {
    return false;
  }
  if (options.queueUntilUnlock === true) {
    return true;
  }
  return (options.priority ?? 'alert') === 'alert';
}

function shouldOpenFollowup(options: DeliverSpokenAlertOptions): boolean {
  if (options.openFollowupWindow === false) {
    return false;
  }
  if (options.openFollowupWindow === true) {
    return true;
  }
  return (options.priority ?? 'alert') === 'alert';
}

function enqueueUntilUnlock(
  alert: SpokenAlertEligibility,
  storage: Pick<Storage, 'getItem' | 'setItem'>,
  options: DeliverSpokenAlertOptions,
): SpokenAlertDeliveryChannel {
  ensureUnlockFlushListener();
  const key = spokenAlertDedupeKey(alert);
  pendingUntilUnlock = pendingUntilUnlock.filter(
    (entry) => spokenAlertDedupeKey(entry.alert) !== key,
  );
  pendingUntilUnlock.push({ alert, storage, options });
  syncQueueSize();
  return 'queued';
}

export function pendingSpokenAlertQueueSize(): number {
  return pendingUntilUnlock.length;
}

/** Test helper — drop queued alerts. */
export function clearQueuedSpokenAlerts(): void {
  pendingUntilUnlock = [];
  syncQueueSize();
}

export async function flushQueuedSpokenAlerts(): Promise<void> {
  if (!isKairoMediaUnlocked() || pendingUntilUnlock.length === 0) {
    return;
  }
  const batch = pendingUntilUnlock;
  pendingUntilUnlock = [];
  syncQueueSize();
  for (const entry of batch) {
    await deliverSpokenOperatorAlert(entry.alert, entry.storage, {
      ...entry.options,
      queueUntilUnlock: false,
      // Already passed shouldSpeakAlert when queued; avoid double-dedupe skip.
      dedupe: false,
    });
  }
}

function markFollowupIfNeeded(options: DeliverSpokenAlertOptions): void {
  if (shouldOpenFollowup(options)) {
    scheduleKairoVoiceFollowupWindowAfterSpeech();
  }
}

export async function deliverSpokenOperatorAlert(
  alert: SpokenAlertEligibility,
  storage: Pick<Storage, 'getItem' | 'setItem'> = sessionStorage,
  options: DeliverSpokenAlertOptions = {},
): Promise<SpokenAlertDeliveryChannel> {
  if (options.dedupe !== false && !shouldSpeakAlert(alert, storage)) {
    return 'skipped';
  }

  if (shouldQueueUntilUnlock(options) && !isKairoMediaUnlocked()) {
    return enqueueUntilUnlock(alert, storage, options);
  }

  if (voiceDeckSpokenAlertHandler && (options.priority ?? 'alert') === 'alert') {
    const handled = await voiceDeckSpokenAlertHandler(alert);
    if (handled) {
      markFollowupIfNeeded(options);
      return 'voice_deck';
    }
  }

  const result = await speakKairoLine(alert.message, {
    priority: options.priority ?? 'alert',
    azureVoiceId: options.azureVoiceId?.trim() || undefined,
  });
  if (result.engine === 'azure') {
    markFollowupIfNeeded(options);
    return 'azure';
  }
  if (result.engine === 'browser') {
    markFollowupIfNeeded(options);
    return 'browser';
  }
  return 'skipped';
}

export { spokenAlertDedupeKey };
