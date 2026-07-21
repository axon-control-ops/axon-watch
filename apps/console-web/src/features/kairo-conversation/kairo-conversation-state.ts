import { ref } from 'vue';

export type KairoConversationPhase = 'idle' | 'listening' | 'thinking' | 'speaking';

export const kairoConversationPhase = ref<KairoConversationPhase>('idle');
export const kairoConversationReply = ref('');
export const kairoConversationError = ref<string | null>(null);
export const kairoLastRoutingReceipt = ref<string | null>(null);
export const kairoLastActionTier = ref<string | null>(null);
export const kairoLastModelReceipt = ref<Record<string, unknown> | null>(null);

export function setKairoConversationPhase(phase: KairoConversationPhase): void {
  // #region agent log
  fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'fc0b35'},body:JSON.stringify({sessionId:'fc0b35',runId:'voice-state',hypothesisId:'H3',location:'kairo-conversation-state.ts:setKairoConversationPhase',message:'Kairo conversation phase transition requested',data:{previous:kairoConversationPhase.value,next:phase,changed:kairoConversationPhase.value!==phase},timestamp:Date.now()})}).catch(()=>{});
  // #endregion
  kairoConversationPhase.value = phase;
}

export function setKairoLastRoutingReceipt(receipt: string | null): void {
  kairoLastRoutingReceipt.value = receipt;
}

export function setKairoLastActionTier(tier: string | null): void {
  kairoLastActionTier.value = tier;
}

export function setKairoLastModelReceipt(receipt: Record<string, unknown> | null): void {
  kairoLastModelReceipt.value = receipt;
}

export function isKairoConversationBusy(): boolean {
  return (
    kairoConversationPhase.value === 'thinking' || kairoConversationPhase.value === 'speaking'
  );
}

export function resetKairoConversationSurface(): void {
  kairoConversationPhase.value = 'idle';
  kairoConversationError.value = null;
}
