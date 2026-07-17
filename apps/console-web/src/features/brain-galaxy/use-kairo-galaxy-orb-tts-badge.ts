import { computed, type Ref } from 'vue';

import {
  kairoVoiceActiveEngine,
  kairoVoiceActiveReason,
  kairoVoiceEngineBadge,
  kairoVoiceLastEngine,
  kairoVoiceLastReason,
} from '../../lib/kairo-voice-diagnostics';

export function useKairoGalaxyOrbTtsBadge(speaking: Ref<boolean>) {
  return computed(() => {
    if (!speaking.value) {
      return '';
    }
    void kairoVoiceActiveEngine.value;
    void kairoVoiceActiveReason.value;
    void kairoVoiceLastEngine.value;
    void kairoVoiceLastReason.value;
    return kairoVoiceEngineBadge();
  });
}
