/** Edit / Resend helpers for OP (and command) messages in the conversation seam. */

import { focusAgentDockComposerInput } from './agent-dock-composer-focus';
import { requestIdeComposerMode } from './ide-composer-restore-request';
import { useShellStore } from '../stores/shell';

/** Command-turn / legacy path — loads text into the bottom composer. */
export function restoreOperatorTextToComposer(text: string): void {
  requestIdeComposerMode('agent');
  useShellStore().restoreComposerDraft(text);
  focusAgentDockComposerInput();
}

/**
 * Cursor regenerate: re-run from the YOU prompt that produced this agent reply.
 * Returns null when there is nothing to regenerate from.
 */
export function agentReplyRegeneratePrompt(
  precedingOperatorContent: string | null | undefined,
): string | null {
  const trimmed = String(precedingOperatorContent ?? '').trim();
  return trimmed || null;
}

/**
 * Submit an edited YOU prompt without leaving it parked in the composer.
 * Temporarily uses the draft for dispatch, then restores the prior draft if
 * submit did not clear it (failure / no-op).
 */
export async function submitOperatorPromptInline(content: string): Promise<boolean> {
  const trimmed = content.trim();
  const shell = useShellStore();
  if (
    !trimmed ||
    shell.commandMutationState === 'submitting' ||
    shell.agentStreamActive
  ) {
    return false;
  }
  requestIdeComposerMode('agent');
  const previousDraft = shell.ideComposerDraft;
  shell.ideComposerDraft = trimmed;
  await shell.submitIdeComposer('agent');
  if (shell.ideComposerDraft.trim() === trimmed) {
    shell.ideComposerDraft = previousDraft;
    return false;
  }
  return true;
}

export async function resendOperatorMessage(content: string): Promise<void> {
  await submitOperatorPromptInline(content);
}

/** Agent-turn regenerate — same dispatch path as YOU Retry. */
export async function regenerateAgentReplyFromPrompt(
  precedingOperatorContent: string | null | undefined,
): Promise<boolean> {
  const prompt = agentReplyRegeneratePrompt(precedingOperatorContent);
  if (!prompt) {
    return false;
  }
  return submitOperatorPromptInline(prompt);
}
