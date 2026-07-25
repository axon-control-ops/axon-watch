/** Edit / Resend helpers for OP (and command) messages in the conversation seam. */

import { focusAgentDockComposerInput } from './agent-dock-composer-focus';
import { requestIdeComposerMode } from './ide-composer-restore-request';
import { useShellStore } from '../stores/shell';

export function restoreOperatorTextToComposer(text: string): void {
  requestIdeComposerMode('agent');
  useShellStore().restoreComposerDraft(text);
  focusAgentDockComposerInput();
}

export async function resendOperatorMessage(content: string): Promise<void> {
  const trimmed = content.trim();
  const shell = useShellStore();
  if (!trimmed || shell.commandMutationState === 'submitting') {
    return;
  }
  requestIdeComposerMode('agent');
  shell.restoreComposerDraft(trimmed);
  await shell.submitIdeComposer('agent');
}
