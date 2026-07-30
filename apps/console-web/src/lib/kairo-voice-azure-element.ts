/** Azure HTMLAudioElement play helpers for Kairo voice (desktop unlock + retry). */

import { isDesktopWebView, unlockKairoAudioPlayback } from './kairo-audio-unlock';

const AUDIO_PREROLL_MS = 160;
const DEFAULT_ENCODED_LEAD_IN_MS = 1100;
// Live 48 kHz MP3 inspection adds codec / neural onset after the SSML silence.
const AZURE_CODEC_ONSET_MS = 280;
/** Data/blob URLs sometimes never fire canplaythrough — never block forever. */
const AUDIO_READY_TIMEOUT_MS = 3500;

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    globalThis.setTimeout(resolve, ms);
  });
}

async function waitForAudioReady(audio: HTMLAudioElement): Promise<void> {
  // Prefer HAVE_ENOUGH_DATA so the leading guard silence is actually buffered.
  const readyEnough = (): boolean => audio.readyState >= HTMLMediaElement.HAVE_ENOUGH_DATA;
  if (readyEnough()) {
    return;
  }
  await new Promise<void>((resolve, reject) => {
    let settled = false;
    const finish = (ok: boolean, error?: Error): void => {
      if (settled) {
        return;
      }
      settled = true;
      cleanup();
      if (ok) {
        resolve();
        return;
      }
      reject(error ?? new Error('audio preload failed'));
    };
    const onReady = (): void => {
      if (readyEnough() || audio.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA) {
        finish(true);
      }
    };
    const onError = (): void => {
      finish(false, new Error('audio preload failed'));
    };
    const timer = globalThis.setTimeout(() => {
      if (audio.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
        finish(true);
        return;
      }
      // Last resort: let play() decide — do not leave SPEAKING stuck forever.
      finish(true);
    }, AUDIO_READY_TIMEOUT_MS);
    const cleanup = (): void => {
      globalThis.clearTimeout(timer);
      audio.removeEventListener('canplay', onReady);
      audio.removeEventListener('canplaythrough', onReady);
      audio.removeEventListener('loadeddata', onReady);
      audio.removeEventListener('error', onError);
    };
    audio.addEventListener('canplay', onReady);
    audio.addEventListener('canplaythrough', onReady);
    audio.addEventListener('loadeddata', onReady);
    audio.addEventListener('error', onError);
  });
}

export function playbackErrorReason(error: unknown): string {
  if (error instanceof DOMException) {
    return `audio_playback_failed:${error.name}`;
  }
  if (error instanceof Error && error.name) {
    return `audio_playback_failed:${error.name}`;
  }
  return 'audio_playback_failed';
}

async function playOnceToCompletion(
  audio: HTMLAudioElement,
  onElementPlaying?: () => void,
): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    let settled = false;
    const finish = (): void => {
      if (settled) {
        return;
      }
      settled = true;
      cleanup();
      resolve();
    };
    const fail = (error?: unknown): void => {
      if (settled) {
        return;
      }
      settled = true;
      cleanup();
      reject(error instanceof Error ? error : new Error('audio playback failed'));
    };
    const cleanup = (): void => {
      audio.onended = null;
      audio.onerror = null;
    };
    audio.onended = finish;
    audio.onerror = () => fail(new Error('audio element error'));
    void audio.play().then(onElementPlaying, (error: unknown) => fail(error));
  });
}

export async function playAzureAudioToCompletion(
  audio: HTMLAudioElement,
  onAudibleStart?: () => void,
  encodedLeadInMs = DEFAULT_ENCODED_LEAD_IN_MS,
): Promise<void> {
  let audibleStartSent = false;
  let audibleStartTimer: ReturnType<typeof globalThis.setTimeout> | null = null;
  const scheduleAudibleStart = (): void => {
    if (audibleStartSent || !onAudibleStart) {
      return;
    }
    audibleStartSent = true;
    audibleStartTimer = globalThis.setTimeout(() => {
      audibleStartTimer = null;
      onAudibleStart();
    }, Math.max(0, encodedLeadInMs + AZURE_CODEC_ONSET_MS));
  };
  // Best-effort unlock for Tauri/WebKit; never block Azure playback on unlock failure.
  if (isDesktopWebView()) {
    try {
      await unlockKairoAudioPlayback();
    } catch {
      // ignore
    }
  }
  audio.preload = 'auto';
  try {
    audio.setAttribute('playsinline', 'true');
  } catch {
    // ignore
  }
  await waitForAudioReady(audio);
  // Do not seek to 0 after buffering — that can discard the primed start and clip.
  await delay(AUDIO_PREROLL_MS);
  try {
    audio.muted = false;
    audio.volume = 1;
  } catch {
    // ignore
  }
  try {
    await playOnceToCompletion(audio, scheduleAudibleStart);
  } catch (firstError) {
    if (audibleStartTimer !== null) {
      globalThis.clearTimeout(audibleStartTimer);
      audibleStartTimer = null;
      audibleStartSent = false;
    }
    // WebKitGTK often rejects the first play() until a media-element unlock
    // lands under a gesture. Retry once after a fresh unlock before falling back.
    if (isDesktopWebView()) {
      try {
        await unlockKairoAudioPlayback();
        await delay(80);
        await playOnceToCompletion(audio, scheduleAudibleStart);
        return;
      } catch (retryError) {
        if (audibleStartTimer !== null) {
          globalThis.clearTimeout(audibleStartTimer);
          audibleStartTimer = null;
        }
        throw new Error(playbackErrorReason(retryError));
      }
    }
    throw new Error(playbackErrorReason(firstError));
  }
}

