import { ref } from 'vue';

/**
 * True while VAXON speech captions / speaker chip should own stage space
 * (utterance in flight or floating caption lines still visible).
 */
export const galaxySpeechOverlayActive = ref(false);

export function setGalaxySpeechOverlayActive(active: boolean): void {
  galaxySpeechOverlayActive.value = active;
}
