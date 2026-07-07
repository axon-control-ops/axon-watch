export const OPEN_IDE_THREAD_TABS_KEY = 'axon-x-open-ide-thread-tabs-v1';
export const ACTIVE_IDE_THREAD_IDS_KEY = 'axon-x-active-ide-thread-v1';

function uniqueThreadIds(values: readonly string[]): string[] {
  const seen = new Set<string>();
  const output: string[] = [];
  for (const value of values) {
    const next = value.trim();
    if (!next || seen.has(next)) {
      continue;
    }
    seen.add(next);
    output.push(next);
  }
  return output;
}

export function readOpenIdeThreadIdsByWorkspace(): Record<string, string[]> {
  if (typeof window === 'undefined') {
    return {};
  }

  try {
    const raw = window.localStorage.getItem(OPEN_IDE_THREAD_TABS_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return {};
    }

    const output: Record<string, string[]> = {};
    for (const [workspaceId, threadIds] of Object.entries(parsed)) {
      if (!workspaceId.trim() || !Array.isArray(threadIds)) {
        continue;
      }
      output[workspaceId] = uniqueThreadIds(threadIds.map((value) => String(value ?? '')));
    }
    return output;
  } catch {
    return {};
  }
}

export function writeOpenIdeThreadIdsForWorkspace(
  workspaceId: string,
  threadIds: readonly string[],
): void {
  if (typeof window === 'undefined') {
    return;
  }

  const id = workspaceId.trim();
  if (!id) {
    return;
  }

  const current = readOpenIdeThreadIdsByWorkspace();
  const next = {
    ...current,
    [id]: uniqueThreadIds(threadIds),
  };

  try {
    window.localStorage.setItem(OPEN_IDE_THREAD_TABS_KEY, JSON.stringify(next));
  } catch {
    // Ignore quota failures.
  }
}

export function readActiveIdeThreadIdsByWorkspace(): Record<string, string> {
  if (typeof window === 'undefined') {
    return {};
  }

  try {
    const raw = window.localStorage.getItem(ACTIVE_IDE_THREAD_IDS_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return {};
    }

    const output: Record<string, string> = {};
    for (const [workspaceId, threadId] of Object.entries(parsed)) {
      const nextWorkspaceId = workspaceId.trim();
      const nextThreadId = String(threadId ?? '').trim();
      if (!nextWorkspaceId || !nextThreadId) {
        continue;
      }
      output[nextWorkspaceId] = nextThreadId;
    }
    return output;
  } catch {
    return {};
  }
}

export function writeActiveIdeThreadIdForWorkspace(workspaceId: string, threadId: string): void {
  if (typeof window === 'undefined') {
    return;
  }

  const nextWorkspaceId = workspaceId.trim();
  const nextThreadId = threadId.trim();
  if (!nextWorkspaceId || !nextThreadId) {
    return;
  }

  const current = readActiveIdeThreadIdsByWorkspace();
  try {
    window.localStorage.setItem(
      ACTIVE_IDE_THREAD_IDS_KEY,
      JSON.stringify({
        ...current,
        [nextWorkspaceId]: nextThreadId,
      }),
    );
  } catch {
    // Ignore quota failures.
  }
}

export function clearActiveIdeThreadIdForWorkspace(workspaceId: string): void {
  if (typeof window === 'undefined') {
    return;
  }

  const nextWorkspaceId = workspaceId.trim();
  if (!nextWorkspaceId) {
    return;
  }

  const current = readActiveIdeThreadIdsByWorkspace();
  if (!(nextWorkspaceId in current)) {
    return;
  }

  const next = { ...current };
  delete next[nextWorkspaceId];
  try {
    window.localStorage.setItem(ACTIVE_IDE_THREAD_IDS_KEY, JSON.stringify(next));
  } catch {
    // Ignore quota failures.
  }
}
