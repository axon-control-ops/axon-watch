/**
 * Azure TTS chunk playback with N+1 prefetch.
 */
import { markKairoVoicePlaybackActive } from './kairo-voice-diagnostics';
import { postKairoTts, type KairoTtsResponse } from './kairo-tts-client';

export type AzureChunkTuning = {
  rate: number;
  pitch: number;
  voice: string;
};

export type AzureChunkHandlers = {
  notifyChunk: (chunkText?: string) => void;
  createAudioHandle: (
    audioBase64: string,
    contentType?: string,
  ) => { audio: HTMLAudioElement; revoke: () => void };
  registerAudio: (audio: HTMLAudioElement | null) => void;
  playToCompletion: (audio: HTMLAudioElement) => Promise<void>;
  speakBrowserFallback: (
    text: string,
    reason: string,
    tuning: AzureChunkTuning,
  ) => Promise<{ engine: 'azure' | 'browser' | 'skipped' | 'idle'; reason: string | null }>;
  resolveFallbackReason: (response: KairoTtsResponse) => string;
  finish: (
    result: { engine: 'azure' | 'browser' | 'skipped' | 'idle'; reason: string | null },
    message: string,
  ) => { engine: 'azure' | 'browser' | 'skipped' | 'idle'; reason: string | null };
  notifySpeaking: (active: boolean) => void;
  notifyIdle: () => void;
  onPlaybackStart: () => void;
};

export async function speakAzureChunksWithPrefetch(
  chunks: string[],
  tuning: AzureChunkTuning,
  handlers: AzureChunkHandlers,
): Promise<{ engine: 'azure' | 'browser' | 'skipped' | 'idle'; reason: string | null }> {
  let prefetch: Promise<KairoTtsResponse> | null = null;
  let lastPrefetchMs: number | null = null;

  for (let index = 0; index < chunks.length; index += 1) {
    const chunk = chunks[index];
    const remaining = chunks.slice(index).join(' ');
    const response =
      (await prefetch) ??
      (await postKairoTts(chunk, {
        rate: tuning.rate,
        pitch: tuning.pitch,
        voice: tuning.voice,
      }));
    prefetch = null;
    if (typeof response.first_byte_ms === 'number') {
      lastPrefetchMs = response.first_byte_ms;
    }
    if (!response.available || !response.audio_base64) {
      return handlers.speakBrowserFallback(
        remaining,
        handlers.resolveFallbackReason(response),
        tuning,
      );
    }
    if (index + 1 < chunks.length) {
      const nextChunk = chunks[index + 1];
      prefetch = postKairoTts(nextChunk, {
        rate: tuning.rate,
        pitch: tuning.pitch,
        voice: tuning.voice,
      }).then((payload) => ({ ...payload, prefetch: true }));
    }
    const azureReason =
      typeof response.first_byte_ms === 'number'
        ? `first_byte_ms=${response.first_byte_ms}`
        : lastPrefetchMs !== null
          ? `first_byte_ms=${lastPrefetchMs}`
          : null;
    markKairoVoicePlaybackActive('azure', azureReason);
    const handle = handlers.createAudioHandle(response.audio_base64, response.content_type);
    handlers.registerAudio(handle.audio);
    try {
      if (index === 0) {
        handlers.onPlaybackStart();
      }
      handlers.notifyChunk(chunk);
      await handlers.playToCompletion(handle.audio);
    } catch (error) {
      handlers.registerAudio(null);
      const reason =
        error instanceof Error && error.message.startsWith('audio_playback_failed')
          ? error.message
          : 'audio_playback_failed';
      return handlers.speakBrowserFallback(remaining, reason, tuning);
    } finally {
      handlers.registerAudio(null);
      handle.revoke();
    }
  }
  handlers.notifySpeaking(false);
  handlers.notifyIdle();
  const reason =
    lastPrefetchMs !== null ? `prefetch_ok;first_byte_ms=${lastPrefetchMs}` : null;
  return handlers.finish({ engine: 'azure', reason }, chunks.join(' '));
}
