import { logKairoVoice } from './kairo-voice-debug';
import { recordKairoVoicePlayback } from './kairo-voice-diagnostics';
import { postKairoTts, type KairoTtsResponse } from './kairo-tts-client';
import { sanitizeSpokenReply, splitSpokenReplyChunks } from './sanitize-spoken-reply';
import {
  isKairoPlaybackActive,
  pauseKairoPlayback,
  registerKairoAudioElement,
  resumeKairoPlayback,
  stopKairoPlayback as stopSharedPlayback,
} from './kairo-playback-control';
import {
  enqueueSpeech,
  stopSpeech,
  subscribeSpeechQueueSpeaking,
  waitForSpeechQueueIdle,
  type SpeechPort,
} from './speech-queue';

export type KairoVoiceEngine = 'azure' | 'browser' | 'skipped' | 'idle';

export type KairoVoicePlaybackResult = {
  engine: KairoVoiceEngine;
  reason: string | null;
};

export type SpeakKairoLineOptions = {
  /** When set, routes through the global voice queue. Default: conversation. */
  priority?: 'interrupt' | 'alert' | 'conversation' | 'narration';
  /** Skip the queue and play immediately (queue worker only). */
  immediate?: boolean;
};

const speakingListeners = new Set<(active: boolean) => void>();
const idleListeners = new Set<() => void>();
const chunkListeners = new Set<() => void>();
let speaking = false;

const AUDIO_PREROLL_MS = 40;

function speechPort(): SpeechPort | null {
  return typeof speechSynthesis === 'undefined' ? null : speechSynthesis;
}

function notifySpeaking(active: boolean): void {
  speaking = active;
  for (const listener of speakingListeners) {
    listener(active);
  }
}

function notifyIdle(): void {
  if (speaking || isKairoPlaybackActive()) {
    return;
  }
  for (const listener of idleListeners) {
    listener();
  }
}

function notifyChunk(): void {
  for (const listener of chunkListeners) {
    listener();
  }
}

export function isKairoVoiceSpeaking(): boolean {
  return speaking || isKairoPlaybackActive();
}

if (typeof window !== 'undefined') {
  subscribeSpeechQueueSpeaking((active) => {
    if (!active) {
      notifySpeaking(isKairoPlaybackActive());
      notifyIdle();
      return;
    }
    notifySpeaking(true);
  });
}

export function subscribeKairoVoiceSpeaking(listener: (active: boolean) => void): () => void {
  speakingListeners.add(listener);
  listener(isKairoVoiceSpeaking());
  return () => {
    speakingListeners.delete(listener);
  };
}

export function onKairoVoiceIdle(listener: () => void): () => void {
  idleListeners.add(listener);
  return () => {
    idleListeners.delete(listener);
  };
}

export function subscribeKairoVoiceChunk(listener: () => void): () => void {
  chunkListeners.add(listener);
  return () => {
    chunkListeners.delete(listener);
  };
}

export function stopKairoPlayback(): void {
  stopSharedPlayback();
  stopSpeech(speechPort());
  notifySpeaking(false);
  notifyIdle();
}

export { pauseKairoPlayback, resumeKairoPlayback };

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    globalThis.setTimeout(resolve, ms);
  });
}

async function waitForAudioReady(audio: HTMLAudioElement): Promise<void> {
  if (audio.readyState >= HTMLMediaElement.HAVE_ENOUGH_DATA) {
    return;
  }
  await new Promise<void>((resolve, reject) => {
    const onReady = (): void => {
      cleanup();
      resolve();
    };
    const onError = (): void => {
      cleanup();
      reject(new Error('audio preload failed'));
    };
    const cleanup = (): void => {
      audio.removeEventListener('canplaythrough', onReady);
      audio.removeEventListener('error', onError);
    };
    audio.addEventListener('canplaythrough', onReady, { once: true });
    audio.addEventListener('error', onError, { once: true });
    audio.load();
  });
}

async function playAzureAudioToCompletion(audio: HTMLAudioElement): Promise<void> {
  audio.preload = 'auto';
  audio.currentTime = 0;
  await waitForAudioReady(audio);
  await delay(AUDIO_PREROLL_MS);
  await new Promise<void>((resolve, reject) => {
    const finish = (): void => {
      cleanup();
      resolve();
    };
    const fail = (): void => {
      cleanup();
      reject(new Error('audio playback failed'));
    };
    const cleanup = (): void => {
      audio.onended = null;
      audio.onerror = null;
    };
    audio.onended = finish;
    audio.onerror = fail;
    void audio.play().catch(fail);
  });
}

async function playAzureAudio(audio: HTMLAudioElement): Promise<void> {
  await playAzureAudioToCompletion(audio);
}

async function speakAzureChunks(chunks: string[]): Promise<KairoVoicePlaybackResult> {
  // If a later Azure chunk fails after earlier ones already played, fall back with
  // ONLY the remaining text. Falling back with chunks.join(' ') re-speaks the
  // Azure audio in browser TTS (neural + robotic double voice).
  for (let index = 0; index < chunks.length; index += 1) {
    const chunk = chunks[index];
    const remaining = chunks.slice(index).join(' ');
    notifyChunk();
    const response = await postKairoTts(chunk);
    if (!response.available || !response.audio_base64) {
      return speakWithBrowser(remaining, resolveAzureFallbackReason(response));
    }
    const audio = new Audio(
      `data:${response.content_type ?? 'audio/mpeg'};base64,${response.audio_base64}`,
    );
    registerKairoAudioElement(audio);
    try {
      await playAzureAudioToCompletion(audio);
    } catch {
      registerKairoAudioElement(null);
      return speakWithBrowser(remaining, 'audio_playback_failed');
    } finally {
      registerKairoAudioElement(null);
    }
  }
  notifySpeaking(false);
  notifyIdle();
  return finishPlayback({ engine: 'azure', reason: null }, chunks.join(' '));
}

function finishPlayback(
  result: KairoVoicePlaybackResult,
  message: string,
): KairoVoicePlaybackResult {
  recordKairoVoicePlayback(result, message);
  logKairoVoice('playback', { engine: result.engine, reason: result.reason, preview: message.slice(0, 80) });
  return result;
}

async function speakWithBrowser(
  text: string,
  reason: string | null = 'azure_unavailable',
): Promise<KairoVoicePlaybackResult> {
  const trimmed = text.trim();
  if (!trimmed) {
    notifySpeaking(false);
    notifyIdle();
    return finishPlayback({ engine: 'skipped', reason: reason ?? 'empty_remainder' }, text);
  }

  const port = speechPort();
  if (!port) {
    notifySpeaking(false);
    notifyIdle();
    return finishPlayback({ engine: 'skipped', reason: 'browser_unavailable' }, trimmed);
  }

  // Ensure Azure HTMLAudioElement is fully released before browser TTS starts.
  stopSharedPlayback();
  notifySpeaking(true);
  await delay(AUDIO_PREROLL_MS);
  for (const chunk of splitSpokenReplyChunks(trimmed)) {
    notifyChunk();
    enqueueSpeech(chunk, port);
  }
  // Must wait for browser TTS to finish — returning early made callers start
  // the next line while the front of this one was still speaking (or clipped).
  await waitForSpeechQueueIdle();
  notifySpeaking(false);
  notifyIdle();
  return finishPlayback({ engine: 'browser', reason }, trimmed);
}

function resolveAzureFallbackReason(response: KairoTtsResponse): string {
  return response.reason?.trim() || 'azure_unavailable';
}

/**
 * Play one sanitized line now. Does not interrupt other jobs — the global
 * voice queue (`enqueueKairoSpeech` / `speakKairoLine`) owns serialization.
 */
export async function playKairoUtteranceNow(
  text: string,
): Promise<KairoVoicePlaybackResult> {
  const trimmed = sanitizeSpokenReply(text);
  if (!trimmed) {
    return finishPlayback({ engine: 'skipped', reason: 'empty_text' }, text);
  }

  notifySpeaking(true);
  const chunks = splitSpokenReplyChunks(trimmed);

  try {
    if (chunks.length === 1) {
      notifyChunk();
      const response = await postKairoTts(chunks[0]);
      if (response.available && response.audio_base64) {
        const audio = new Audio(
          `data:${response.content_type ?? 'audio/mpeg'};base64,${response.audio_base64}`,
        );
        registerKairoAudioElement(audio);
        try {
          await playAzureAudio(audio);
          notifySpeaking(false);
          notifyIdle();
          return finishPlayback({ engine: 'azure', reason: null }, trimmed);
        } catch {
          registerKairoAudioElement(null);
          return speakWithBrowser(trimmed, 'audio_playback_failed');
        }
      }
      return speakWithBrowser(trimmed, resolveAzureFallbackReason(response));
    }
    return await speakAzureChunks(chunks);
  } catch (error) {
    logKairoVoice('tts_error', {
      message: error instanceof Error ? error.message : String(error),
    });
    return speakWithBrowser(trimmed, 'fetch_error');
  }
}

/**
 * Queue (default) or immediately play a Kairo line. Concurrent callers no
 * longer interrupt each other mid-word — only barge-in flushes the queue.
 */
export async function speakKairoLine(
  text: string,
  options: SpeakKairoLineOptions = {},
): Promise<KairoVoicePlaybackResult> {
  if (options.immediate) {
    return playKairoUtteranceNow(text);
  }
  const { enqueueKairoSpeech } = await import('./kairo-voice-queue');
  return enqueueKairoSpeech(text, {
    priority: options.priority ?? 'conversation',
  });
}

/** @deprecated Use speakKairoLine() and read `.engine` */
export async function speakKairoLineEngine(text: string): Promise<KairoVoiceEngine> {
  const result = await speakKairoLine(text);
  return result.engine === 'idle' ? 'skipped' : result.engine;
}

export { stopSpeech };
