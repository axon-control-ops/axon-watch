/**
 * Unlock HTMLAudioElement playback inside Tauri/WebKitGTK.
 * Without a prior gesture, Azure MP3 play() rejects and we fall back to
 * robotic speechSynthesis.
 */

import { readonly, ref } from 'vue';

let unlocked = false;
let mediaUnlocked = false;
let unlockPromise: Promise<boolean> | null = null;

const unlockListeners = new Set<() => void>();

/** Reactive snapshot for shell chrome (banner / HUD). */
const unlockSnapshot = ref({
  unlocked: false,
  mediaUnlocked: false,
});

export const kairoAudioUnlockSnapshot = readonly(unlockSnapshot);

function syncSnapshot(): void {
  unlockSnapshot.value = {
    unlocked,
    mediaUnlocked,
  };
}

function notifyUnlocked(): void {
  syncSnapshot();
  for (const listener of [...unlockListeners]) {
    try {
      listener();
    } catch {
      // ignore listener errors
    }
  }
}

export function isDesktopWebView(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }
  return Boolean(
    window.__TAURI_INTERNALS__ ||
      window.__TAURI__ ||
      window.__AXON_DESKTOP__ ||
      (typeof navigator !== 'undefined' && /Tauri/i.test(navigator.userAgent)),
  );
}

async function unlockAudioContext(): Promise<boolean> {
  try {
    const Ctx =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctx) {
      return false;
    }
    const ctx = new Ctx();
    if (ctx.state === 'suspended') {
      await ctx.resume();
    }
    const buffer = ctx.createBuffer(1, 1, 22050);
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    source.start(0);
    await ctx.close();
    return true;
  } catch {
    return false;
  }
}

async function unlockHtmlAudioElement(): Promise<boolean> {
  try {
    // Tiny silent WAV — WebKit needs a successful HTMLAudioElement.play()
    // under a user gesture; AudioContext alone is not enough for MP3 later.
    const silentWav =
      'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQQAAAAAAA==';
    const audio = new Audio(silentWav);
    audio.volume = 0.01;
    try {
      audio.setAttribute('playsinline', 'true');
    } catch {
      // ignore
    }
    await audio.play();
    audio.pause();
    audio.src = '';
    mediaUnlocked = true;
    return true;
  } catch {
    return false;
  }
}

async function attemptUnlock(): Promise<boolean> {
  if (unlocked && mediaUnlocked) {
    return true;
  }
  const wasMedia = mediaUnlocked;
  const contextOk = await unlockAudioContext();
  const mediaOk = await unlockHtmlAudioElement();
  unlocked = contextOk || mediaOk || unlocked;
  syncSnapshot();
  if (mediaUnlocked && !wasMedia) {
    notifyUnlocked();
  }
  return unlocked && mediaUnlocked;
}

/** Call from first user gesture (click/keydown). Safe to call repeatedly. */
export function unlockKairoAudioPlayback(): Promise<boolean> {
  if (unlocked && mediaUnlocked) {
    return Promise.resolve(true);
  }
  if (!unlockPromise) {
    unlockPromise = attemptUnlock().finally(() => {
      unlockPromise = null;
    });
  }
  return unlockPromise;
}

/** Subscribe to successful media unlock (Azure-ready). Returns unsubscribe. */
export function onKairoAudioUnlocked(listener: () => void): () => void {
  unlockListeners.add(listener);
  if (mediaUnlocked) {
    try {
      listener();
    } catch {
      // ignore
    }
  }
  return () => {
    unlockListeners.delete(listener);
  };
}

export function installKairoAudioUnlockListeners(): () => void {
  if (typeof window === 'undefined' || typeof document === 'undefined') {
    return () => undefined;
  }
  const onGesture = () => {
    void unlockKairoAudioPlayback();
  };
  const opts: AddEventListenerOptions = { capture: true, passive: true };
  window.addEventListener('pointerdown', onGesture, opts);
  window.addEventListener('keydown', onGesture, opts);
  window.addEventListener('touchstart', onGesture, opts);
  // Desktop webview: also try once on load (may still need a gesture).
  if (isDesktopWebView()) {
    void unlockKairoAudioPlayback();
  }
  syncSnapshot();
  return () => {
    window.removeEventListener('pointerdown', onGesture, opts);
    window.removeEventListener('keydown', onGesture, opts);
    window.removeEventListener('touchstart', onGesture, opts);
  };
}

export function isKairoAudioUnlocked(): boolean {
  return unlocked;
}

export function isKairoMediaUnlocked(): boolean {
  return mediaUnlocked;
}

/** True when Azure/HTMLAudio playback is allowed after a gesture. */
export function isKairoVoicePlaybackArmed(): boolean {
  return mediaUnlocked;
}

/** Test helper — reset unlock state between Vitest cases. */
export function resetKairoAudioUnlockState(): void {
  unlocked = false;
  mediaUnlocked = false;
  unlockPromise = null;
  unlockListeners.clear();
  syncSnapshot();
}
