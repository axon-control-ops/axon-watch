/** Stable storage key so composer drafts/modes stay isolated per conversation tab. */
export function composerThreadScopeKey(
  workspaceId: string | null | undefined,
  threadId: string | null | undefined,
): string | null {
  const workspace = String(workspaceId ?? '').trim();
  const thread = String(threadId ?? '').trim();
  if (!workspace || !thread) {
    return null;
  }
  return `${workspace}::${thread}`;
}
