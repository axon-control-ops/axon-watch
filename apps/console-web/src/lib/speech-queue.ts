/** Serialize browser speech synthesis so lines do not clip each other. */

export type SpeechPort = Pick<SpeechSynthesis, 'speak' | 'getVoices'> & {
  cancel?: SpeechSynthesis['cancel'];
  pause?: SpeechSynthesis['pause'];
  resume?: SpeechSynthesis['resume'];
  speaking?: boolean;
  paused?: boolean;
  addEventListener?: SpeechSynthesis['addEventListener'];
};

let queue: string[] = [];
let speaking = false;
let voicesReady = false;
let cachedVoice: SpeechSynthesisVoice | null = null;
const speakingListeners = new Set<(active: boolean) => void>();
const idleListeners = new Set<() => void>();

function notifySpeaking(active: boolean): void {
  speaking = active;
  for (const listener of speakingListeners) {
    listener(active);
  }
}

function notifyIdle(): void {
  if (speaking || queue.length > 0) {
    return;
  }
  for (const listener of idleListeners) {
    listener();
  }
}

const JARVIS_VOICE_PREFS = [
  /ryan.*neural/i,
  /en-gb.*ryan/i,
  /george.*neural/i,
  /en-gb.*george/i,
  /daniel.*neural/i,
  /en-gb.*daniel/i,
  /microsoft.*david/i,
  /google.*uk.*english.*male/i,
  /\bneural\b/i,
];

function pickJarvisVoice(speech: SpeechPort): SpeechSynthesisVoice | null {
  if (cachedVoice) {
    return cachedVoice;
  }
  const voices = speech.getVoices();
  if (!voices.length) {
    return null;
  }
  for (const pref of JARVIS_VOICE_PREFS) {
    const match = voices.find((voice) => pref.test(`${voice.name} ${voice.voiceURI}`));
    if (match) {
      cachedVoice = match;
      return match;
    }
  }
  cachedVoice =
    voices.find((voice) => voice.lang.startsWith('en-GB') && !voice.localService) ??
    voices.find((voice) => voice.lang.startsWith('en-GB')) ??
    voices.find((voice) => voice.lang.startsWith('en') && !voice.localService) ??
    voices.find((voice) => voice.lang.startsWith('en')) ??
    voices[0] ??
    null;
  return cachedVoice;
}

function warmSpeechIfNeeded(speech: SpeechPort): void {
  if (voicesReady) {
    return;
  }
  speech.getVoices();
  if (typeof speech.addEventListener === 'function') {
    speech.addEventListener('voiceschanged', () => {
      cachedVoice = null;
      pickJarvisVoice(speech);
    });
  }
  voicesReady = true;
}

function drainQueue(speech: SpeechPort): void {
  if (speaking || queue.length === 0) {
    notifyIdle();
    return;
  }
  if (typeof SpeechSynthesisUtterance === 'undefined') {
    queue = [];
    notifySpeaking(false);
    notifyIdle();
    return;
  }

  notifySpeaking(true);
  const text = queue.shift() ?? '';
  const utterance = new SpeechSynthesisUtterance(text);
  // Keep browser fallback at natural defaults — slowed/lowered pitch sounded robotic.
  utterance.rate = 1;
  utterance.pitch = 1;
  utterance.volume = 1;
  const voice = pickJarvisVoice(speech);
  if (voice) {
    utterance.voice = voice;
  }

  const finish = (): void => {
    notifySpeaking(false);
    globalThis.setTimeout(() => {
      drainQueue(speech);
      notifyIdle();
    }, 220);
  };

  utterance.onend = finish;
  utterance.onerror = finish;

  globalThis.setTimeout(() => {
    speech.speak(utterance);
  }, 60);
}

export function enqueueSpeech(message: string, speech: SpeechPort | null): void {
  const trimmed = message.trim();
  if (!trimmed || !speech) {
    return;
  }
  warmSpeechIfNeeded(speech);
  queue.push(trimmed);
  drainQueue(speech);
}

export function resetSpeechQueue(): void {
  stopSpeech(null);
}

export function stopSpeech(speech: SpeechPort | null): void {
  queue = [];
  if (speech && typeof speech.cancel === 'function') {
    speech.cancel();
  }
  notifySpeaking(false);
  notifyIdle();
}

export function isSpeechQueueSpeaking(): boolean {
  return speaking;
}

export function isSpeechQueueBusy(): boolean {
  return speaking || queue.length > 0;
}

/**
 * Resolve when the browser speech queue has fully drained (all chunks finished).
 * Callers that enqueue then return early used to think speech was done while
 * TTS was still mid-utterance — that caused clipped / late-start overlaps.
 */
export function waitForSpeechQueueIdle(): Promise<void> {
  if (!isSpeechQueueBusy()) {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    const unsubscribe = onSpeechQueueIdle(() => {
      if (isSpeechQueueBusy()) {
        return;
      }
      unsubscribe();
      resolve();
    });
  });
}

export function subscribeSpeechQueueSpeaking(
  listener: (active: boolean) => void,
): () => void {
  speakingListeners.add(listener);
  listener(speaking);
  return () => {
    speakingListeners.delete(listener);
  };
}

export function onSpeechQueueIdle(listener: () => void): () => void {
  idleListeners.add(listener);
  return () => {
    idleListeners.delete(listener);
  };
}
