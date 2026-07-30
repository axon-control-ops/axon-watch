let memoryDismissedDoneIds = new Set<string>();

const DISMISSED_DONE_KEY = 'axon-x-task-board-dismissed-done-v1';

function readDismissedDoneIds(): Set<string> {
  if (typeof sessionStorage === 'undefined') {
    return new Set(memoryDismissedDoneIds);
  }
  try {
    const raw = sessionStorage.getItem(DISMISSED_DONE_KEY);
    if (!raw) {
      return new Set(memoryDismissedDoneIds);
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return new Set(memoryDismissedDoneIds);
    }
    return new Set(
      parsed.filter((item): item is string => typeof item === 'string' && item.trim().length > 0),
    );
  } catch {
    return new Set(memoryDismissedDoneIds);
  }
}

function persistDismissedDoneIds(ids: Set<string>): void {
  memoryDismissedDoneIds = new Set(ids);
  if (typeof sessionStorage === 'undefined') {
    return;
  }
  try {
    sessionStorage.setItem(DISMISSED_DONE_KEY, JSON.stringify([...ids]));
  } catch {
    // Ignore quota / private-mode failures; memory set still applies for the session.
  }
}

/** Session-local hide for completed task-board tickets (no server archive API). */
export function loadDismissedDoneTaskIds(): Set<string> {
  return readDismissedDoneIds();
}

export function dismissDoneTaskId(taskId: string, current: Set<string>): Set<string> {
  const cleaned = taskId.trim();
  if (!cleaned) {
    return current;
  }
  const next = new Set(current);
  next.add(cleaned);
  persistDismissedDoneIds(next);
  return next;
}

export function dismissDoneTaskIds(taskIds: string[], current: Set<string>): Set<string> {
  const next = new Set(current);
  for (const taskId of taskIds) {
    const cleaned = taskId.trim();
    if (cleaned) {
      next.add(cleaned);
    }
  }
  persistDismissedDoneIds(next);
  return next;
}

export function clearDismissedDoneTaskIds(): Set<string> {
  const empty = new Set<string>();
  persistDismissedDoneIds(empty);
  return empty;
}
