import { ref } from 'vue';

import type { KairoVoicePlaybackResult } from './kairo-voice-playback';

export const kairoVoiceLastEngine = ref<KairoVoicePlaybackResult['engine']>('idle');
export const kairoVoiceLastReason = ref<string | null>(null);
export const kairoVoiceLastAt = ref<string | null>(null);
export const kairoVoiceLastPreview = ref('');

export function recordKairoVoicePlayback(
  result: KairoVoicePlaybackResult,
  message: string,
): void {
  kairoVoiceLastEngine.value = result.engine;
  kairoVoiceLastReason.value = result.reason;
  kairoVoiceLastAt.value = new Date().toISOString();
  kairoVoiceLastPreview.value = message.trim().slice(0, 120);
}

export function resetKairoVoiceDiagnostics(): void {
  kairoVoiceLastEngine.value = 'idle';
  kairoVoiceLastReason.value = null;
  kairoVoiceLastAt.value = null;
  kairoVoiceLastPreview.value = '';
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
