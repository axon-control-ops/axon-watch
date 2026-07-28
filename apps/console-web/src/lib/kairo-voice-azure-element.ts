/** Azure HTMLAudioElement play helpers for Kairo voice (desktop unlock + retry). */

import { isDesktopWebView, unlockKairoAudioPlayback } from './kairo-audio-unlock';

const AUDIO_PREROLL_MS = 40;
/** Data/blob URLs sometimes never fire canplaythrough — never block forever. */
const AUDIO_READY_TIMEOUT_MS = 2500;

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    globalThis.setTimeout(resolve, ms);
  });
}

async function waitForAudioReady(audio: HTMLAudioElement): Promise<void> {
  // Prefer HAVE_FUTURE_DATA so the first phonemes are buffered before play().
  const readyEnough = (): boolean => audio.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA;
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
      if (readyEnough() || audio.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
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

async function playOnceToCompletion(audio: HTMLAudioElement): Promise<void> {
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
    void audio.play().then(undefined, (error: unknown) => fail(error));
  });
}

export async function playAzureAudioToCompletion(audio: HTMLAudioElement): Promise<void> {
  const playbackStartedAt = performance.now();
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
  // #region agent log
  fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'standup-voice',hypothesisId:'S1',location:'kairo-voice-azure-element.ts:before-play',message:'starting synthesized audio element',data:{currentTime:audio.currentTime,duration:Number.isFinite(audio.duration)?audio.duration:null,readyState:audio.readyState,paused:audio.paused,ended:audio.ended,muted:audio.muted,volume:audio.volume},timestamp:Date.now()})}).catch(()=>{});
  // #endregion
  try {
    await playOnceToCompletion(audio);
    // #region agent log
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'standup-voice',hypothesisId:'S1',location:'kairo-voice-azure-element.ts:after-play',message:'synthesized audio element completed',data:{currentTime:audio.currentTime,duration:Number.isFinite(audio.duration)?audio.duration:null,readyState:audio.readyState,paused:audio.paused,ended:audio.ended,muted:audio.muted,volume:audio.volume,elapsedMs:Math.round(performance.now()-playbackStartedAt)},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
  } catch (firstError) {
    // WebKitGTK often rejects the first play() until a media-element unlock
    // lands under a gesture. Retry once after a fresh unlock before falling back.
    if (isDesktopWebView()) {
      try {
        await unlockKairoAudioPlayback();
        await delay(80);
        await playOnceToCompletion(audio);
        return;
      } catch (retryError) {
        throw new Error(playbackErrorReason(retryError));
      }
    }
    throw new Error(playbackErrorReason(firstError));
  }
}

