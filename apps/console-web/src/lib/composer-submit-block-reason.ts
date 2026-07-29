export function composerSubmitBlockReason(
  workspaceId: string | null | undefined,
  content: string,
  commandMutationState?: string,
  agentStreamActive?: boolean,
): string | null {
  if (commandMutationState === 'submitting') {
    return 'Chat is already submitting — wait a moment, then retry.';
  }
  if (agentStreamActive) {
    return 'Agent is still streaming — wait for it to finish, or queue a follow-up from Agent mode.';
  }
  if (!workspaceId) {
    return 'Select a workspace before sending.';
  }
  if (!content) {
    return 'Composer draft is empty — nothing to send.';
  }
  return null;
}
