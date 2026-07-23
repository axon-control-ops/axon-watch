import {
  isSpeechQueueSpeaking,
  stopSpeech,
  type SpeechPort,
} from './speech-queue';

let paused = false;
let currentAudio: HTMLAudioElement | null = null;

function speechPort(): SpeechPort | null {
  return typeof speechSynthesis === 'undefined' ? null : speechSynthesis;
}

export function registerKairoAudioElement(audio: HTMLAudioElement | null): void {
  currentAudio = audio;
}

export function isKairoPlaybackPaused(): boolean {
  return paused;
}

export function isKairoPlaybackActive(): boolean {
  if (paused) {
    return true;
  }
  if (currentAudio && !currentAudio.paused && !currentAudio.ended) {
    return true;
  }
  return isSpeechQueueSpeaking();
}

export function pauseKairoPlayback(): boolean {
  const speech = speechPort();
  if (speech && 'pause' in speech && typeof speech.pause === 'function' && speech.speaking && !speech.paused) {
    speech.pause();
    paused = true;
    return true;
  }
  if (currentAudio && !currentAudio.paused && !currentAudio.ended) {
    currentAudio.pause();
    paused = true;
    return true;
  }
  return false;
}

export function resumeKairoPlayback(): boolean {
  const speech = speechPort();
  if (paused && speech && 'resume' in speech && typeof speech.resume === 'function' && speech.paused) {
    speech.resume();
    paused = false;
    return true;
  }
  if (paused && currentAudio && currentAudio.paused) {
    void currentAudio.play();
    paused = false;
    return true;
  }
  return false;
}

export function duckKairoPlaybackGain(factor: number): void {
  const clamped = Math.max(0, Math.min(1, factor));
  if (currentAudio) {
    currentAudio.volume = clamped;
  }
}

export function restoreKairoPlaybackGain(): void {
  if (currentAudio) {
    currentAudio.volume = 1;
  }
}

export function stopKairoPlayback(): void {
  paused = false;
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.src = '';
    currentAudio.volume = 1;
    currentAudio = null;
  }
  stopSpeech(speechPort());
}
