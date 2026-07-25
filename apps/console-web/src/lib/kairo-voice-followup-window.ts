import { ref } from 'vue';

import { isKairoVoiceSpeaking, onKairoVoiceIdle } from './kairo-voice-playback';

/** How long hands-free follow-ups stay open after VAXON finishes speaking. */
export const KAIRO_VOICE_FOLLOWUP_WINDOW_MS = 30_000;

export const kairoVoiceFollowupExpiresAt = ref<number | null>(null);
const followupPendingAfterSpeech = ref(false);

export function isKairoVoiceFollowupWindowActive(now = Date.now()): boolean {
  const expiresAt = kairoVoiceFollowupExpiresAt.value;
  return expiresAt !== null && now < expiresAt;
}

export function kairoVoiceFollowupRemainingMs(now = Date.now()): number {
  const expiresAt = kairoVoiceFollowupExpiresAt.value;
  if (expiresAt === null) {
    return 0;
  }
  return Math.max(0, expiresAt - now);
}

export function openKairoVoiceFollowupWindow(now = Date.now()): void {
  kairoVoiceFollowupExpiresAt.value = now + KAIRO_VOICE_FOLLOWUP_WINDOW_MS;
}

export function clearKairoVoiceFollowupWindow(): void {
  kairoVoiceFollowupExpiresAt.value = null;
  followupPendingAfterSpeech.value = false;
}

export function scheduleKairoVoiceFollowupWindowAfterSpeech(): void {
  followupPendingAfterSpeech.value = true;
}

export function finalizeKairoVoiceFollowupWindow(): void {
  if (!followupPendingAfterSpeech.value) {
    return;
  }
  if (isKairoVoiceSpeaking()) {
    return;
  }
  followupPendingAfterSpeech.value = false;
  openKairoVoiceFollowupWindow();
}

if (typeof window !== 'undefined') {
  onKairoVoiceIdle(() => {
    finalizeKairoVoiceFollowupWindow();
  });
}
