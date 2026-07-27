import { ref } from 'vue';

/** Armed when the operator opens an in-thread shell card in the bottom terminal. */
export const agentShellMirrorActive = ref(false);

/**
 * Optional explicit snapshot for a clicked `:::terminal` card.
 * When set, the dock prefers this text over "latest open segment".
 */
export const agentShellMirrorForcedText = ref<string | null>(null);

/** Queued command to inject into the interactive operator bash PTY. */
export const pendingOperatorTerminalCommand = ref<string | null>(null);

/** Queued command to run in the vaxon agent PTY (Continue in background). */
export const pendingAgentBackgroundCommand = ref<string | null>(null);

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

export function queueOperatorTerminalCommand(command: string): void {
  const trimmed = command.trim();
  if (!trimmed) {
    return;
  }
  pendingOperatorTerminalCommand.value = trimmed;
}

export function takePendingOperatorTerminalCommand(): string | null {
  const command = pendingOperatorTerminalCommand.value;
  pendingOperatorTerminalCommand.value = null;
  return command;
}

export function queueAgentBackgroundCommand(command: string): void {
  const trimmed = command.trim();
  if (!trimmed) {
    return;
  }
  // Leave mirror mode so the live agent PTY can accept the command.
  clearAgentShellMirrorForcedText();
  clearAgentShellMirror();
  pendingAgentBackgroundCommand.value = trimmed;
}

export function takePendingAgentBackgroundCommand(): string | null {
  const command = pendingAgentBackgroundCommand.value;
  pendingAgentBackgroundCommand.value = null;
  return command;
}
