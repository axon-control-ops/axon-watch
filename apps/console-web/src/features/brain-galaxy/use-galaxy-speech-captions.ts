import { onBeforeUnmount, onMounted, ref } from 'vue';

import { subscribeKairoVoiceChunk } from '../../lib/kairo-voice-playback';
import { subscribeKairoVoiceUtterance } from '../../lib/kairo-voice-utterance';
import {
  buildNarrationSentenceSteps,
  GALAXY_CAPTION_FLOAT_MS,
  GALAXY_CAPTION_MAX_VISIBLE,
  type GalaxySpeechCaption,
} from './galaxy-speech-captions-view';

let nextCaptionId = 0;

export function useGalaxySpeechCaptions() {
  const captions = ref<GalaxySpeechCaption[]>([]);
  const timers: number[] = [];
  let unsubscribeUtterance: (() => void) | null = null;
  let unsubscribeChunk: (() => void) | null = null;
  let generation = 0;
  let utteranceActive = false;

  function clearTimers(): void {
    for (const timer of timers.splice(0, timers.length)) {
      window.clearTimeout(timer);
    }
  }

  function pruneCaption(id: string): void {
    captions.value = captions.value.filter((caption) => caption.id !== id);
  }

  function pushCaption(text: string, gen: number): void {
    if (gen !== generation || !text.trim()) {
      return;
    }
    const caption: GalaxySpeechCaption = {
      id: `galaxy-cap-${++nextCaptionId}`,
      text: text.trim(),
      bornAt: Date.now(),
    };
    captions.value = [...captions.value, caption].slice(-GALAXY_CAPTION_MAX_VISIBLE);
    const removeTimer = window.setTimeout(() => {
      pruneCaption(caption.id);
    }, GALAXY_CAPTION_FLOAT_MS);
    timers.push(removeTimer);
  }

  /** Narration chunk started — show its sentences one at a time from this moment. */
  function onNarrationChunk(chunkText: string): void {
    if (!utteranceActive) {
      return;
    }
    clearTimers();
    generation += 1;
    const gen = generation;
    const steps = buildNarrationSentenceSteps(chunkText);
    if (steps.length === 0) {
      return;
    }
    for (const step of steps) {
      if (step.delayMs <= 0) {
        pushCaption(step.phrase, gen);
        continue;
      }
      const timer = window.setTimeout(() => {
        pushCaption(step.phrase, gen);
      }, step.delayMs);
      timers.push(timer);
    }
  }

  function startUtterance(): void {
    utteranceActive = true;
    clearTimers();
    captions.value = [];
    generation += 1;
  }

  function endUtterance(): void {
    utteranceActive = false;
    generation += 1;
    clearTimers();
    // Let the visible line finish its CSS float.
  }

  onMounted(() => {
    unsubscribeUtterance = subscribeKairoVoiceUtterance((text) => {
      if (text) {
        startUtterance();
        return;
      }
      endUtterance();
    });
    unsubscribeChunk = subscribeKairoVoiceChunk((chunkText) => {
      onNarrationChunk(chunkText);
    });
  });

  onBeforeUnmount(() => {
    unsubscribeUtterance?.();
    unsubscribeChunk?.();
    unsubscribeUtterance = null;
    unsubscribeChunk = null;
    clearTimers();
    captions.value = [];
  });

  return { captions };
}
