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

/** Empty untitled IDE threads created by "+" — not real conversation history. */
export function isPlaceholderIdeThreadLabel(label: string | null | undefined): boolean {
  const trimmed = String(label || '').trim().toLowerCase();
  return !trimmed || trimmed === 'new chat';
}

function firstSubstantialThreadId(
  ids: readonly string[],
  previewById: Record<string, string>,
): string | null {
  for (const raw of ids) {
    const id = raw?.trim();
    if (!id) {
      continue;
    }
    if (!isPlaceholderIdeThreadLabel(previewById[id])) {
      return id;
    }
  }
  return null;
}

/**
 * Prefer selected → open tab → thread list when bootstrapping IDE chat.
 * If the selected/open tab is an empty "New chat", jump to a titled history thread.
 */
export function resolveBootstrapIdeThreadId(input: {
  selectedThreadId: string | null | undefined;
  openTabIds: readonly string[];
  threadListIds: readonly string[];
  /** Map of thread_id → preview_label for preferring real history. */
  threadPreviewById?: Record<string, string>;
}): string | null {
  const previewById = input.threadPreviewById ?? {};
  const selected = input.selectedThreadId?.trim() || null;

  if (selected && !isPlaceholderIdeThreadLabel(previewById[selected])) {
    return selected;
  }

  const preferred =
    firstSubstantialThreadId(input.openTabIds, previewById) ||
    firstSubstantialThreadId(input.threadListIds, previewById);

  if (preferred) {
    return preferred;
  }

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
