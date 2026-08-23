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

/**
 * Roster-owned teammate tabs use a stable "Name · Role" label until the first
 * message lands. These look like history but are usually empty shells.
 */
export function isEmployeeTitleThreadPreview(previewLabel: string | null | undefined): boolean {
  const label = String(previewLabel || '').trim();
  if (!label || label.toLowerCase() === 'new chat') {
    return true;
  }
  return /^.+ · .+$/.test(label) && label.length <= 48;
}

export function isConversationalThreadPreview(previewLabel: string | null | undefined): boolean {
  const label = String(previewLabel || '').trim();
  if (!label || label.toLowerCase() === 'new chat') {
    return false;
  }
  return !isEmployeeTitleThreadPreview(label);
}

export type IdeThreadBootstrapRecord = {
  thread_id: string;
  preview_label?: string | null;
  updated_at?: string;
};

function previewForThread(
  thread: IdeThreadBootstrapRecord,
  previewById: Record<string, string>,
): string {
  return String(thread.preview_label ?? previewById[thread.thread_id] ?? '').trim();
}

function isBootstrapPlaceholderPreview(label: string | null | undefined): boolean {
  return isPlaceholderIdeThreadLabel(label) || isEmployeeTitleThreadPreview(label);
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

function normalizeBootstrapThreads(input: {
  selectedThreadId?: string | null;
  openTabIds?: readonly string[];
  threadListIds?: readonly string[];
  threads?: readonly IdeThreadBootstrapRecord[];
  threadPreviewById?: Record<string, string>;
}): IdeThreadBootstrapRecord[] {
  const previewById = input.threadPreviewById ?? {};
  const ids = new Set<string>();
  for (const raw of [
    input.selectedThreadId,
    ...(input.openTabIds ?? []),
    ...(input.threadListIds ?? []),
    ...(input.threads ?? []).map((thread) => thread.thread_id),
  ]) {
    const id = String(raw ?? '').trim();
    if (id) {
      ids.add(id);
    }
  }

  if (input.threads?.length) {
    const byId = new Map(input.threads.map((thread) => [thread.thread_id, thread]));
    return [...ids].map((thread_id) => {
      const found = byId.get(thread_id);
      if (found) {
        return {
          thread_id,
          preview_label: found.preview_label ?? previewById[thread_id] ?? null,
          updated_at: found.updated_at,
        };
      }
      return {
        thread_id,
        preview_label: previewById[thread_id] ?? null,
      };
    });
  }

  return [...ids].map((thread_id) => ({
    thread_id,
    preview_label: previewById[thread_id] ?? null,
  }));
}

/**
 * Prefer selected → open tab → thread list when bootstrapping IDE chat.
 * If the selected/open tab is an empty "New chat" or an unused teammate shell,
 * jump to the newest thread that actually has conversation preview text.
 */
export function resolveBootstrapIdeThreadId(input: {
  selectedThreadId: string | null | undefined;
  openTabIds: readonly string[];
  threadListIds?: readonly string[];
  threads?: readonly IdeThreadBootstrapRecord[];
  /** Map of thread_id → preview_label for preferring real history. */
  threadPreviewById?: Record<string, string>;
}): string | null {
  const threads = normalizeBootstrapThreads({
    selectedThreadId: input.selectedThreadId,
    openTabIds: input.openTabIds,
    threadListIds: input.threadListIds,
    threads: input.threads,
    threadPreviewById: input.threadPreviewById,
  });
  const previewById = Object.fromEntries(
    threads.map((thread) => [thread.thread_id, previewForThread(thread, input.threadPreviewById ?? {})]),
  );
  const threadListIds = threads.map((thread) => thread.thread_id);
  const selected = input.selectedThreadId?.trim() || null;

  if (selected && isConversationalThreadPreview(previewById[selected])) {
    return selected;
  }

  const sorted = [...threads].sort((left, right) =>
    String(right.updated_at || '').localeCompare(String(left.updated_at || '')),
  );
  const latestConversational = sorted.find((thread) =>
    isConversationalThreadPreview(previewForThread(thread, previewById)),
  );
  if (latestConversational) {
    return latestConversational.thread_id;
  }

  if (selected && !isPlaceholderIdeThreadLabel(previewById[selected])) {
    return selected;
  }

  const preferred =
    firstSubstantialThreadId(input.openTabIds, previewById) ||
    firstSubstantialThreadId(threadListIds, previewById);

  if (preferred) {
    return preferred;
  }

  if (selected && !isBootstrapPlaceholderPreview(previewById[selected])) {
    return selected;
  }

  const fromTabs = input.openTabIds[0]?.trim();
  if (fromTabs) {
    return fromTabs;
  }
  return threadListIds[0]?.trim() || null;
}
