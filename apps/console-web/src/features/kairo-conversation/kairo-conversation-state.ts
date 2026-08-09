import { ref } from 'vue';

export type KairoConversationPhase = 'idle' | 'listening' | 'thinking' | 'speaking';

export type KairoConversationTurn = {
  role: 'operator' | 'vaxon';
  content: string;
  at: string;
};

export const kairoConversationPhase = ref<KairoConversationPhase>('idle');
export const kairoConversationReply = ref('');
export const kairoConversationThread = ref<KairoConversationTurn[]>([]);
export const kairoConversationError = ref<string | null>(null);
export const kairoLastRoutingReceipt = ref<string | null>(null);
export const kairoLastActionTier = ref<string | null>(null);
export const kairoLastModelReceipt = ref<Record<string, unknown> | null>(null);

function _nowStamp(): string {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

export function pushKairoTurn(role: KairoConversationTurn['role'], content: string): void {
  const trimmed = content.trim();
  if (!trimmed) return;
  kairoConversationThread.value = [
    ...kairoConversationThread.value.slice(-39),
    { role, content: trimmed, at: _nowStamp() },
  ];
}

export function clearKairoConversationThread(): void {
  kairoConversationThread.value = [];
}

export function setKairoConversationPhase(phase: KairoConversationPhase): void {
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
