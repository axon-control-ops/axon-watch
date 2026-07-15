import { ref } from 'vue';

export type KairoConversationPhase = 'idle' | 'listening' | 'thinking' | 'speaking';

export const kairoConversationPhase = ref<KairoConversationPhase>('idle');
export const kairoConversationReply = ref('');
export const kairoConversationError = ref<string | null>(null);
export const kairoLastRoutingReceipt = ref<string | null>(null);
export const kairoLastActionTier = ref<string | null>(null);

export function setKairoConversationPhase(phase: KairoConversationPhase): void {
  kairoConversationPhase.value = phase;
}

export function setKairoLastRoutingReceipt(receipt: string | null): void {
  kairoLastRoutingReceipt.value = receipt;
}

export function setKairoLastActionTier(tier: string | null): void {
  kairoLastActionTier.value = tier;
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
