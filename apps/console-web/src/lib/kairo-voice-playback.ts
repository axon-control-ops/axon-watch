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
import { enqueueSpeech, stopSpeech, subscribeSpeechQueueSpeaking, type SpeechPort } from './speech-queue';

export type KairoVoiceEngine = 'azure' | 'browser' | 'skipped' | 'idle';

export type KairoVoicePlaybackResult = {
  engine: KairoVoiceEngine;
  reason: string | null;
};

const speakingListeners = new Set<(active: boolean) => void>();
const idleListeners = new Set<() => void>();
const chunkListeners = new Set<() => void>();
let speaking = false;

const AUDIO_PREROLL_MS = 40;
const PLAYBACK_HANDOFF_MS = 50;

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
  for (const chunk of chunks) {
    notifyChunk();
    const response = await postKairoTts(chunk);
    if (!response.available || !response.audio_base64) {
      return speakWithBrowser(chunks.join(' '), resolveAzureFallbackReason(response));
    }
    const audio = new Audio(
      `data:${response.content_type ?? 'audio/mpeg'};base64,${response.audio_base64}`,
    );
    registerKairoAudioElement(audio);
    try {
      await playAzureAudioToCompletion(audio);
    } catch {
      registerKairoAudioElement(null);
      return speakWithBrowser(chunks.join(' '), 'audio_playback_failed');
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
  const port = speechPort();
  if (!port) {
    notifySpeaking(false);
    notifyIdle();
    return finishPlayback({ engine: 'skipped', reason: 'browser_unavailable' }, text);
  }

  notifySpeaking(true);
  await delay(AUDIO_PREROLL_MS);
  for (const chunk of splitSpokenReplyChunks(text)) {
    notifyChunk();
    enqueueSpeech(chunk, port);
  }
  return finishPlayback({ engine: 'browser', reason }, text);
}

function resolveAzureFallbackReason(response: KairoTtsResponse): string {
  return response.reason?.trim() || 'azure_unavailable';
}

export async function speakKairoLine(text: string): Promise<KairoVoicePlaybackResult> {
  const trimmed = sanitizeSpokenReply(text);
  if (!trimmed) {
    return finishPlayback({ engine: 'skipped', reason: 'empty_text' }, text);
  }

  if (isKairoPlaybackActive()) {
    stopKairoPlayback();
    await delay(PLAYBACK_HANDOFF_MS);
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

/** @deprecated Use speakKairoLine() and read `.engine` */
export async function speakKairoLineEngine(text: string): Promise<KairoVoiceEngine> {
  const result = await speakKairoLine(text);
  return result.engine === 'idle' ? 'skipped' : result.engine;
}

export { stopSpeech };
