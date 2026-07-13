import { ref } from 'vue';

/** Armed when the operator opens an in-thread shell card in the bottom terminal. */
export const agentShellMirrorActive = ref(false);

/**
 * Optional explicit snapshot for a clicked `:::terminal` card.
 * When set, the dock prefers this text over "latest open segment".
 */
export const agentShellMirrorForcedText = ref<string | null>(null);

export function armAgentShellMirror(): void {
  agentShellMirrorActive.value = true;
}

export function clearAgentShellMirror(): void {
  agentShellMirrorActive.value = false;
}

export function queueAgentShellMirrorText(text: string): void {
  const trimmed = text.replace(/\s+$/g, '');
  if (!trimmed) {
    return;
  }
  agentShellMirrorForcedText.value = `${trimmed}\n`;
  armAgentShellMirror();
}

export function clearAgentShellMirrorForcedText(): void {
  agentShellMirrorForcedText.value = null;
}
