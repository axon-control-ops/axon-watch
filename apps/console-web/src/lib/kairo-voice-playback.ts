import { logKairoVoice } from './kairo-voice-debug';
import {
  clearKairoVoicePlaybackActive,
  markKairoVoicePlaybackActive,
  recordKairoVoicePlayback,
} from './kairo-voice-diagnostics';
import { postKairoTts, isAzureTtsBlocked, azureTtsBlockedReasonValue, type KairoTtsResponse } from './kairo-tts-client';
import { speakAzureChunksWithPrefetch } from './kairo-voice-azure-prefetch';
import {
  playAzureAudioToCompletion,
  playbackErrorReason,
} from './kairo-voice-azure-element';
import { sanitizeSpokenReply, splitSpokenReplyChunks } from './sanitize-spoken-reply';
import { reportTheaterOpen } from '../features/report-theater/report-theater-state';
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
import {
  notifyKairoVoiceUtterance,
  type KairoVoiceSpeaker,
} from './kairo-voice-utterance';

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
  /** Prefer local browser TTS to avoid Azure request latency. */
  preferBrowser?: boolean;
  /** Playback rate for Azure SSML + browser utterance (axon-local 0.50–1.30). */
  speechRate?: number;
  /** Playback pitch for Azure SSML + browser utterance (axon-local 0.50–1.50). */
  speechPitch?: number;
  /** Azure neural voice id (falls back to presence settings / server default). */
  azureVoiceId?: string;
  /** Who is speaking — drives Galaxy speaker avatar popup. */
  speaker?: KairoVoiceSpeaker | null;
  /** Command Theater narration may speak while stand-up holds the floor. */
  allowDuringReportTheater?: boolean;
};

const speakingListeners = new Set<(active: boolean) => void>();
const idleListeners = new Set<() => void>();
const chunkListeners = new Set<(chunkText: string) => void>();
let speaking = false;

type VoiceTuning = { rate: number; pitch: number; voice: string };

let speechTuningProvider: () => VoiceTuning = () => ({
  rate: 1.0,
  pitch: 1.04,
  voice: 'en-GB-RyanNeural',
});

/** Wire operator presence speech_rate / speech_pitch / azure_voice_id. */
export function setKairoSpeechTuningProvider(provider: () => VoiceTuning): void {
  speechTuningProvider = provider;
}

/** @deprecated Use setKairoSpeechTuningProvider */
export function setKairoSpeechRateProvider(provider: () => number): void {
  speechTuningProvider = () => ({
    rate: provider(),
    pitch: 1.04,
    voice: 'en-GB-RyanNeural',
  });
}

function resolveSpeechTuning(options: {
  speechRate?: number;
  speechPitch?: number;
  azureVoiceId?: string;
} = {}): VoiceTuning {
  const fromSettings = speechTuningProvider();
  const rateRaw =
    typeof options.speechRate === 'number' && Number.isFinite(options.speechRate)
      ? options.speechRate
      : fromSettings.rate;
  const pitchRaw =
    typeof options.speechPitch === 'number' && Number.isFinite(options.speechPitch)
      ? options.speechPitch
      : fromSettings.pitch;
  const voice =
    typeof options.azureVoiceId === 'string' && options.azureVoiceId.trim()
      ? options.azureVoiceId.trim()
      : fromSettings.voice;
  return {
    rate: Math.max(0.5, Math.min(1.3, rateRaw)),
    pitch: Math.max(0.5, Math.min(1.5, pitchRaw)),
    voice: voice || 'en-GB-RyanNeural',
  };
}

const AUDIO_PREROLL_MS = 120;
let browserPrerollArmed = true;
function speechPort(): SpeechPort | null {
  return typeof speechSynthesis === 'undefined' ? null : speechSynthesis;
}

type AzureAudioHandle = {
  audio: HTMLAudioElement;
  revoke: () => void;
};

function createAzureAudioHandle(
  audioBase64: string,
  contentType?: string,
): AzureAudioHandle {
  const mime = (contentType ?? 'audio/mpeg').split(';')[0]?.trim() || 'audio/mpeg';
  let objectUrl: string | null = null;
  try {
    const binary = atob(audioBase64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }
    objectUrl = URL.createObjectURL(new Blob([bytes], { type: mime }));
    const audio = new Audio(objectUrl);
    audio.preload = 'auto';
    try {
      audio.setAttribute('playsinline', 'true');
    } catch {
      // FakeAudio / older stubs may not implement setAttribute.
    }
    return {
      audio,
      revoke: () => {
        if (objectUrl) {
          URL.revokeObjectURL(objectUrl);
          objectUrl = null;
        }
      },
    };
  } catch {
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
    }
    const audio = new Audio(`data:${mime};base64,${audioBase64}`);
    audio.preload = 'auto';
    try {
      audio.setAttribute('playsinline', 'true');
    } catch {
      // ignore
    }
    return {
      audio,
      revoke: () => undefined,
    };
  }
}

function notifySpeaking(active: boolean): void {
  speaking = active;
  if (!active) {
    notifyKairoVoiceUtterance(null);
  }
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

function notifyChunk(chunkText = ''): void {
  const text = chunkText.trim();
  for (const listener of chunkListeners) {
    listener(text);
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

export function subscribeKairoVoiceChunk(
  listener: (chunkText: string) => void,
): () => void {
  chunkListeners.add(listener);
  return () => {
    chunkListeners.delete(listener);
  };
}

export function stopKairoPlayback(): void {
  browserPrerollArmed = true;
  stopSharedPlayback();
  stopSpeech(speechPort());
  notifyKairoVoiceUtterance(null);
  notifySpeaking(false);
  notifyIdle();
  clearKairoVoicePlaybackActive();
}

export { pauseKairoPlayback, resumeKairoPlayback };

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    globalThis.setTimeout(resolve, ms);
  });
}

async function playAzureAudio(audio: HTMLAudioElement): Promise<void> {
  await playAzureAudioToCompletion(audio);
}

async function speakAzureChunks(
  chunks: string[],
  tuning: VoiceTuning,
): Promise<KairoVoicePlaybackResult> {
  return speakAzureChunksWithPrefetch(chunks, tuning, {
    notifyChunk,
    createAudioHandle: createAzureAudioHandle,
    registerAudio: registerKairoAudioElement,
    playToCompletion: playAzureAudioToCompletion,
    speakBrowserFallback: speakWithBrowser,
    resolveFallbackReason: resolveAzureFallbackReason,
    finish: finishPlayback,
    notifySpeaking,
    notifyIdle,
  });
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
  tuning: VoiceTuning = { rate: 1.0, pitch: 1.04, voice: 'en-GB-RyanNeural' },
  speaker: KairoVoiceSpeaker | null = null,
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

  const browserChunks = splitSpokenReplyChunks(trimmed);

  // Ensure Azure HTMLAudioElement is fully released before browser TTS starts.
  stopSharedPlayback();
  notifyKairoVoiceUtterance(trimmed, speaker);
  notifySpeaking(true);
  markKairoVoicePlaybackActive('browser', reason);
  if (browserPrerollArmed) {
    await delay(AUDIO_PREROLL_MS);
    browserPrerollArmed = false;
  }
  for (const chunk of browserChunks) {
    enqueueSpeech(chunk, port, {
      rate: tuning.rate,
      pitch: tuning.pitch,
      voiceHint: speaker?.azureVoiceId?.trim() || speaker?.id,
      onStart: () => {
        notifyChunk(chunk);
      },
    });
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
  options: {
    preferBrowser?: boolean;
    speechRate?: number;
    speechPitch?: number;
    azureVoiceId?: string;
    speaker?: KairoVoiceSpeaker | null;
  } = {},
): Promise<KairoVoicePlaybackResult> {
  const trimmed = sanitizeSpokenReply(text);
  const tuning = resolveSpeechTuning(options);
  const speaker = options.speaker ?? null;
  if (!trimmed) {
    return finishPlayback({ engine: 'skipped', reason: 'empty_text' }, text);
  }

  if (options.preferBrowser || isAzureTtsBlocked()) {
    // #region agent log
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'voice-gender-fix',hypothesisId:'H49',location:'kairo-voice-playback.ts:skip-azure',message:'skipping Azure TTS for browser path',data:{preferBrowser:Boolean(options.preferBrowser),azureBlocked:azureTtsBlockedReasonValue(),textLength:trimmed.length,speaker:speaker?.displayName??null,azureVoiceId:speaker?.azureVoiceId??options.azureVoiceId??null},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    return speakWithBrowser(
      trimmed,
      options.preferBrowser ? 'preferred_browser' : azureTtsBlockedReasonValue() || 'azure_blocked',
      tuning,
      speaker,
    );
  }

  notifyKairoVoiceUtterance(trimmed, speaker);
  notifySpeaking(true);
  markKairoVoicePlaybackActive('azure', null);
  const chunks = splitSpokenReplyChunks(trimmed);

  try {
    if (chunks.length === 1) {
      const response = await postKairoTts(chunks[0], {
        rate: tuning.rate,
        pitch: tuning.pitch,
        voice: tuning.voice,
      });
      if (response.available && response.audio_base64) {
        const azureReason =
          typeof response.first_byte_ms === 'number'
            ? `first_byte_ms=${response.first_byte_ms}`
            : null;
        markKairoVoicePlaybackActive('azure', azureReason);
        const handle = createAzureAudioHandle(response.audio_base64, response.content_type);
        registerKairoAudioElement(handle.audio);
        try {
          notifyChunk(chunks[0]);
          await playAzureAudio(handle.audio);
          notifySpeaking(false);
          notifyIdle();
          return finishPlayback({ engine: 'azure', reason: azureReason }, trimmed);
        } catch (error) {
          registerKairoAudioElement(null);
          const reason =
            error instanceof Error && error.message.startsWith('audio_playback_failed')
              ? error.message
              : playbackErrorReason(error);
          return speakWithBrowser(trimmed, reason, tuning, speaker);
        } finally {
          registerKairoAudioElement(null);
          handle.revoke();
        }
      }
      return speakWithBrowser(trimmed, resolveAzureFallbackReason(response), tuning, speaker);
    }
    return await speakAzureChunks(chunks, tuning);
  } catch (error) {
    logKairoVoice('tts_error', {
      message: error instanceof Error ? error.message : String(error),
    });
    return speakWithBrowser(trimmed, 'fetch_error', tuning, speaker);
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
    if (
      reportTheaterOpen.value &&
      !options.allowDuringReportTheater
    ) {
      return { engine: 'skipped', reason: 'report_theater_lock' };
    }
    return playKairoUtteranceNow(text, {
      preferBrowser: options.preferBrowser,
      speechRate: options.speechRate,
      speechPitch: options.speechPitch,
      azureVoiceId: options.azureVoiceId,
      speaker: options.speaker,
    });
  }
  const { enqueueKairoSpeech } = await import('./kairo-voice-queue');
  return enqueueKairoSpeech(text, {
    priority: options.priority ?? 'conversation',
    preferBrowser: options.preferBrowser,
    speechRate: options.speechRate,
    speechPitch: options.speechPitch,
    azureVoiceId: options.azureVoiceId,
    speaker: options.speaker ?? undefined,
    allowDuringReportTheater: options.allowDuringReportTheater,
  });
}

/** @deprecated Use speakKairoLine() and read `.engine` */
export async function speakKairoLineEngine(text: string): Promise<KairoVoiceEngine> {
  const result = await speakKairoLine(text);
  return result.engine === 'idle' ? 'skipped' : result.engine;
}

export { stopSpeech };
