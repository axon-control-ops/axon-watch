export function openIdeThreadTab(openIds: readonly string[], threadId: string): string[] {
  const id = threadId.trim();
  if (!id || openIds.includes(id)) {
    return [...openIds];
  }
  return [...openIds, id];
}

export function closeIdeThreadTab(openIds: readonly string[], threadId: string): string[] {
  const id = threadId.trim();
  return openIds.filter((item) => item !== id);
}

export function resolveIdeThreadTabAfterClose(input: {
  openIds: readonly string[];
  closedId: string;
  activeId: string | null;
}): string | null {
  if (input.activeId !== input.closedId) {
    return input.activeId;
  }

  const remaining = closeIdeThreadTab(input.openIds, input.closedId);
  if (!remaining.length) {
    return null;
  }

  const closedIndex = input.openIds.indexOf(input.closedId);
  const nextIndex = Math.min(Math.max(closedIndex, 0), remaining.length - 1);
  return remaining[nextIndex] ?? remaining[0] ?? null;
}

export function pruneOpenIdeThreadTabs(
  openIds: readonly string[],
  knownThreadIds: readonly string[],
): string[] {
  const known = new Set(knownThreadIds);
  return openIds.filter((id) => known.has(id));
}

export function ensureOpenIdeThreadTabs(
  openIds: readonly string[],
  fallbackThreadId: string | null,
): string[] {
  if (openIds.length) {
    return [...openIds];
  }
  if (fallbackThreadId?.trim()) {
    return [fallbackThreadId.trim()];
  }
  return [];
}

export function ideThreadTabTitle(previewLabel: string | null | undefined): string {
  return previewLabel?.trim() || 'New chat';
}

export interface IdeThreadTabItem {
  thread_id: string;
  workspace_id: string;
  run_id: string | null;
  thread_kind: string;
  created_at: string;
  updated_at: string;
  preview_label: string;
}

export function resolveOpenIdeThreadTabItems(input: {
  openIds: readonly string[];
  threads: readonly IdeThreadTabItem[];
  activeThreadId: string | null;
  workspaceId: string;
}): IdeThreadTabItem[] {
  const byId = new Map(input.threads.map((thread) => [thread.thread_id, thread]));
  let tabIds = [...input.openIds];

  if (input.activeThreadId && !tabIds.includes(input.activeThreadId)) {
    tabIds = openIdeThreadTab(tabIds, input.activeThreadId);
  }

  if (!tabIds.length && input.activeThreadId) {
    tabIds = [input.activeThreadId];
  }

  return tabIds.map((threadId) => {
    const found = byId.get(threadId);
    if (found) {
      return found;
    }
    return {
      thread_id: threadId,
      workspace_id: input.workspaceId,
      run_id: null,
      thread_kind: 'ide',
      created_at: '',
      updated_at: '',
      preview_label: 'New chat',
    };
  });
}
