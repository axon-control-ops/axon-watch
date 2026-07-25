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

/** True when every open tab is an untitled empty chat (or missing from catalog). */
export function openIdeTabsAreOnlyPlaceholders(
  openIds: readonly string[],
  threads: readonly { thread_id: string; preview_label: string }[],
): boolean {
  if (!openIds.length) {
    return true;
  }
  const byId = new Map(threads.map((thread) => [thread.thread_id, thread.preview_label]));
  return openIds.every((id) => {
    const label = byId.get(id);
    const trimmed = String(label || '').trim().toLowerCase();
    return !trimmed || trimmed === 'new chat';
  });
}

/**
 * When the tab strip is only empty "New chat" slots, reopen recent titled history
 * so past conversations are one click away again.
 */
export function seedOpenIdeTabsFromHistory(input: {
  openIds: readonly string[];
  threads: readonly { thread_id: string; preview_label: string; updated_at?: string }[];
  activeThreadId: string | null;
  maxTabs?: number;
}): string[] {
  const maxTabs = input.maxTabs ?? 6;
  const sorted = [...input.threads].sort((left, right) =>
    String(right.updated_at || '').localeCompare(String(left.updated_at || '')),
  );
  const historyIds = sorted
    .filter((thread) => {
      const label = String(thread.preview_label || '').trim().toLowerCase();
      return Boolean(label) && label !== 'new chat';
    })
    .map((thread) => thread.thread_id);

  if (!historyIds.length) {
    return ensureOpenIdeThreadTabs(input.openIds, input.activeThreadId);
  }

  if (!openIdeTabsAreOnlyPlaceholders(input.openIds, input.threads)) {
    return ensureOpenIdeThreadTabs(input.openIds, input.activeThreadId);
  }

  let next = historyIds.slice(0, maxTabs);
  if (input.activeThreadId?.trim() && !next.includes(input.activeThreadId.trim())) {
    next = [input.activeThreadId.trim(), ...next].slice(0, maxTabs);
  }
  return next;
}

export function ideThreadTabTitle(previewLabel: string | null | undefined): string {
  return previewLabel?.trim() || 'New chat';
}

export interface IdeThreadTabItem {
  thread_id: string;
  workspace_id: string;
  run_id: string | null;
  thread_kind: string;
  employee_id?: string | null;
  employee_role?: string | null;
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
      employee_id: null,
      employee_role: null,
      created_at: '',
      updated_at: '',
      preview_label: 'New chat',
    };
  });
}
