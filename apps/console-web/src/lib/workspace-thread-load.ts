import type { ThreadSurface } from './thread-surface-view';

export function buildWorkspaceThreadLoadKey(
  workspaceId: string,
  surface: ThreadSurface,
  threadId?: string | null,
): string {
  const target = threadId?.trim() || 'auto';
  return `${workspaceId}:${surface}:${target}`;
}

/** Ignore stale history responses when the operator switched tabs mid-flight. */
export function shouldApplyWorkspaceThreadLoad(
  selectedThreadId: string | null | undefined,
  loadedThreadId: string,
): boolean {
  const selected = selectedThreadId?.trim();
  if (!selected) {
    return true;
  }
  return selected === loadedThreadId.trim();
}

/** Prefer selected → open tab → thread list when bootstrapping IDE chat. */
export function resolveBootstrapIdeThreadId(input: {
  selectedThreadId: string | null | undefined;
  openTabIds: readonly string[];
  threadListIds: readonly string[];
}): string | null {
  const selected = input.selectedThreadId?.trim();
  if (selected) {
    return selected;
  }
  const fromTabs = input.openTabIds[0]?.trim();
  if (fromTabs) {
    return fromTabs;
  }
  const fromList = input.threadListIds[0]?.trim();
  return fromList || null;
}
