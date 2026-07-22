/** Reactive text currently being spoken — keeps RUN TRANSCRIPT / speaker chips in sync. */

import { onBeforeUnmount, onMounted, ref } from 'vue';

import {
  getKairoVoiceUtterance,
  subscribeKairoVoiceUtterance,
} from '../lib/kairo-voice-utterance';
import { stripAgentStreamFenceMarkers } from '../lib/agent-live-line-view';

export function useSpokenUtteranceText() {
  const spokenText = ref<string | null>(getKairoVoiceUtterance());

  let unsubscribe: (() => void) | null = null;

  onMounted(() => {
    unsubscribe = subscribeKairoVoiceUtterance((state) => {
      const next = state.text?.trim() ? stripAgentStreamFenceMarkers(state.text) : null;
      spokenText.value = next || null;
      // #region agent log
      fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'fc0b35'},body:JSON.stringify({sessionId:'fc0b35',runId:'post-fix',hypothesisId:'S1',location:'useSpokenUtteranceText.ts:subscribe',message:'spoken utterance for transcript sync',data:{hasText:Boolean(spokenText.value),preview:(spokenText.value??'').slice(0,80),hasFence:/:::/.test(state.text??'')},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
    });
  });

  onBeforeUnmount(() => {
    unsubscribe?.();
    unsubscribe = null;
  });

  return { spokenText };
}
