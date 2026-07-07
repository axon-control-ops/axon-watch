import { ref } from 'vue';

export type KairoConversationPhase = 'idle' | 'listening' | 'thinking' | 'speaking';

export const kairoConversationPhase = ref<KairoConversationPhase>('idle');
export const kairoConversationReply = ref('');
export const kairoConversationError = ref<string | null>(null);

export function setKairoConversationPhase(phase: KairoConversationPhase): void {
  kairoConversationPhase.value = phase;
}

export function resetKairoConversationSurface(): void {
  kairoConversationPhase.value = 'idle';
  kairoConversationError.value = null;
}
