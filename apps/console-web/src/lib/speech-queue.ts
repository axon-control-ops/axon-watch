/** Serialize browser speech synthesis so lines do not clip each other. */

export type SpeechPort = Pick<SpeechSynthesis, 'speak' | 'getVoices'> & {
  addEventListener?: SpeechSynthesis['addEventListener'];
};

let queue: string[] = [];
let speaking = false;
let voicesReady = false;
let cachedVoice: SpeechSynthesisVoice | null = null;

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
    return;
  }
  if (typeof SpeechSynthesisUtterance === 'undefined') {
    queue = [];
    return;
  }

  speaking = true;
  const text = queue.shift() ?? '';
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.88;
  utterance.pitch = 0.92;
  utterance.volume = 1;
  const voice = pickJarvisVoice(speech);
  if (voice) {
    utterance.voice = voice;
  }

  utterance.onend = () => {
    speaking = false;
    window.setTimeout(() => drainQueue(speech), 220);
  };
  utterance.onerror = () => {
    speaking = false;
    window.setTimeout(() => drainQueue(speech), 220);
  };

  speech.speak(utterance);
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
  queue = [];
  speaking = false;
}
