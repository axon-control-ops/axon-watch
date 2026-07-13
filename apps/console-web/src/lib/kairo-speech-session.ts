/** Stable KAIRO session id scoped to workspace + active chat thread (M1). */
export function buildKairoSpeechSessionId(
  workspaceId: string,
  threadId: string | null | undefined,
): string {
  const workspace = workspaceId.trim() || 'default';
  const thread = threadId?.trim() || 'default';
  return `kairo:${workspace}:${thread}`;
}
