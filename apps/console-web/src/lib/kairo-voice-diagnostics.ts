import { ref } from 'vue';

import type { KairoVoicePlaybackResult } from './kairo-voice-playback';

export const kairoVoiceLastEngine = ref<KairoVoicePlaybackResult['engine']>('idle');
export const kairoVoiceLastReason = ref<string | null>(null);
export const kairoVoiceLastAt = ref<string | null>(null);
export const kairoVoiceLastPreview = ref('');

/** Live engine while an utterance is playing (orb badge reads this first). */
export const kairoVoiceActiveEngine = ref<'azure' | 'browser' | null>(null);
export const kairoVoiceActiveReason = ref<string | null>(null);

export function markKairoVoicePlaybackActive(
  engine: 'azure' | 'browser',
  reason: string | null = null,
): void {
  kairoVoiceActiveEngine.value = engine;
  kairoVoiceActiveReason.value = reason;
}

export function clearKairoVoicePlaybackActive(): void {
  kairoVoiceActiveEngine.value = null;
  kairoVoiceActiveReason.value = null;
}

export function recordKairoVoicePlayback(
  result: KairoVoicePlaybackResult,
  message: string,
): void {
  kairoVoiceLastEngine.value = result.engine;
  kairoVoiceLastReason.value = result.reason;
  kairoVoiceLastAt.value = new Date().toISOString();
  kairoVoiceLastPreview.value = message.trim().slice(0, 120);
  clearKairoVoicePlaybackActive();
}

export function resetKairoVoiceDiagnostics(): void {
  kairoVoiceLastEngine.value = 'idle';
  kairoVoiceLastReason.value = null;
  kairoVoiceLastAt.value = null;
  kairoVoiceLastPreview.value = '';
  clearKairoVoicePlaybackActive();
}

export function kairoVoiceDiagnosticsLabel(): string {
  if (kairoVoiceLastEngine.value === 'idle') {
    return 'TTS idle';
  }
  const engine = kairoVoiceLastEngine.value.toUpperCase();
  if (kairoVoiceLastReason.value) {
    return `TTS ${engine} · fallback: ${kairoVoiceLastReason.value}`;
  }
  return `TTS ${engine}`;
}

/** Short operator-facing badge while VAXON is speaking. */
export function kairoVoiceEngineBadge(): string {
  const engine = kairoVoiceActiveEngine.value ?? kairoVoiceLastEngine.value;
  const reason = kairoVoiceActiveReason.value ?? kairoVoiceLastReason.value;
  if (engine === 'azure') {
    return 'Azure voice';
  }
  if (engine === 'browser') {
    return reason ? `Browser voice · ${reason}` : 'Browser voice';
  }
  return '';
}
