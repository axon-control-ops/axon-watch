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
  // #region agent log
  fetch('http://127.0.0.1:7852/ingest/0173158c-fd82-46b4-a14c-d55e0685ee25',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'df24bc'},body:JSON.stringify({sessionId:'df24bc',runId:'kairo-playback-control',hypothesisId:'R7',location:'kairo-playback-control.ts:resumeKairoPlayback',message:'playback resume requested',data:{paused,hasAudio:Boolean(currentAudio),audioPaused:currentAudio?.paused??null,audioEnded:currentAudio?.ended??null,audioCurrentTime:currentAudio?.currentTime??null,speechPaused:speech?.paused??null},timestamp:Date.now()})}).catch(()=>{});
  // #endregion
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

export function stopKairoPlayback(): void {
  paused = false;
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.src = '';
    currentAudio = null;
  }
  stopSpeech(speechPort());
}
