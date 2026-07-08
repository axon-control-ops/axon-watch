import { postKairoTts } from './kairo-tts-client';
import {
  isKairoPlaybackActive,
  pauseKairoPlayback,
  registerKairoAudioElement,
  resumeKairoPlayback,
  stopKairoPlayback as stopSharedPlayback,
} from './kairo-playback-control';
import { enqueueSpeech, stopSpeech, subscribeSpeechQueueSpeaking, type SpeechPort } from './speech-queue';

export type KairoVoiceEngine = 'azure' | 'browser' | 'skipped';

const speakingListeners = new Set<(active: boolean) => void>();
const idleListeners = new Set<() => void>();
let speaking = false;

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

export function stopKairoPlayback(): void {
  stopSharedPlayback();
  notifySpeaking(false);
  notifyIdle();
}

export { pauseKairoPlayback, resumeKairoPlayback };

async function speakWithBrowser(text: string): Promise<KairoVoiceEngine> {
  const port = speechPort();
  if (!port) {
    notifySpeaking(false);
    notifyIdle();
    return 'skipped';
  }

  notifySpeaking(true);
  enqueueSpeech(text, port);
  return 'browser';
}

export async function speakKairoLine(text: string): Promise<KairoVoiceEngine> {
  const trimmed = text.trim();
  if (!trimmed) {
    return 'skipped';
  }

  stopKairoPlayback();
  notifySpeaking(true);

  try {
    const response = await postKairoTts(trimmed);
    if (response.available && response.audio_base64) {
      const audio = new Audio(
        `data:${response.content_type ?? 'audio/mpeg'};base64,${response.audio_base64}`,
      );
      registerKairoAudioElement(audio);
      audio.onended = () => {
        registerKairoAudioElement(null);
        notifySpeaking(false);
        notifyIdle();
      };
      audio.onerror = () => {
        registerKairoAudioElement(null);
        void speakWithBrowser(trimmed);
      };
      await audio.play();
      return 'azure';
    }
  } catch {
    // Fall through to browser TTS.
  }

  return speakWithBrowser(trimmed);
}
