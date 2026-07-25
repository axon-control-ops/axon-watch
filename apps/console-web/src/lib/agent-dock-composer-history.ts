const AGENT_COMPOSER_HISTORY_KEY = 'axon-x-agent-composer-history-v2';
const HISTORY_LIMIT = 25;

export interface AgentDockComposerHistoryKeyEvent {
  key: string;
  shiftKey: boolean;
  altKey?: boolean;
  ctrlKey?: boolean;
  metaKey?: boolean;
  selectionStart: number;
  selectionEnd: number;
  value: string;
}

export interface AgentDockComposerHistoryStepInput {
  entries: string[];
  index: number;
  scratch: string;
  currentDraft: string;
  direction: 'previous' | 'next';
}

export interface AgentDockComposerHistoryStepResult {
  index: number;
  scratch: string;
  draft: string;
}

function normalizeHistoryEntries(entries: string[]): string[] {
  const seen = new Set<string>();
  const normalized: string[] = [];

  for (const entry of entries) {
    const trimmed = entry.trim();
    if (!trimmed || seen.has(trimmed)) {
      continue;
    }
    seen.add(trimmed);
    normalized.push(trimmed);
    if (normalized.length >= HISTORY_LIMIT) {
      break;
    }
  }

  return normalized;
}

function readStoredAgentComposerHistoryByWorkspace(): Record<string, string[]> {
  if (typeof window === 'undefined') {
    return {};
  }

  const raw = window.localStorage.getItem(AGENT_COMPOSER_HISTORY_KEY);
  if (!raw) {
    return {};
  }

  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return {};
    }

    const output: Record<string, string[]> = {};
    for (const [workspaceId, entries] of Object.entries(parsed)) {
      const id = workspaceId.trim();
      if (!id || !Array.isArray(entries)) {
        continue;
      }
      output[id] = normalizeHistoryEntries(
        entries.filter((entry): entry is string => typeof entry === 'string'),
      );
    }
    return output;
  } catch {
    return {};
  }
}

export function readStoredAgentComposerHistory(workspaceId: string | null | undefined): string[] {
  const id = workspaceId?.trim();
  if (!id) {
    return [];
  }
  return readStoredAgentComposerHistoryByWorkspace()[id] ?? [];
}

export function persistAgentComposerHistory(
  workspaceId: string | null | undefined,
  entries: string[],
): void {
  if (typeof window === 'undefined') {
    return;
  }

  const id = workspaceId?.trim();
  if (!id) {
    return;
  }

  const current = readStoredAgentComposerHistoryByWorkspace();
  window.localStorage.setItem(
    AGENT_COMPOSER_HISTORY_KEY,
    JSON.stringify({
      ...current,
      [id]: normalizeHistoryEntries(entries),
    }),
  );
}

export function recordAgentComposerHistoryEntry(entries: string[], draft: string): string[] {
  const trimmed = draft.trim();
  if (!trimmed) {
    return normalizeHistoryEntries(entries);
  }
  return normalizeHistoryEntries([trimmed, ...entries]);
}

function hasHistoryModifiers(event: AgentDockComposerHistoryKeyEvent): boolean {
  return Boolean(event.shiftKey || event.altKey || event.ctrlKey || event.metaKey);
}

export function shouldRecallPreviousAgentComposerHistory(
  event: AgentDockComposerHistoryKeyEvent,
): boolean {
  if (event.key !== 'ArrowUp' || hasHistoryModifiers(event)) {
    return false;
  }
  if (event.selectionStart !== event.selectionEnd) {
    return false;
  }
  return !event.value.slice(0, event.selectionStart).includes('\n');
}

export function shouldRecallNextAgentComposerHistory(
  event: AgentDockComposerHistoryKeyEvent,
  browsingHistory: boolean,
): boolean {
  if (!browsingHistory || event.key !== 'ArrowDown' || hasHistoryModifiers(event)) {
    return false;
  }
  return event.selectionStart === event.selectionEnd;
}

export function stepAgentComposerHistory(
  input: AgentDockComposerHistoryStepInput,
): AgentDockComposerHistoryStepResult {
  const entries = normalizeHistoryEntries(input.entries);
  if (!entries.length) {
    return {
      index: -1,
      scratch: input.currentDraft,
      draft: input.currentDraft,
    };
  }

  if (input.direction === 'previous') {
    const nextIndex = Math.min(input.index + 1, entries.length - 1);
    return {
      index: nextIndex,
      scratch: input.index === -1 ? input.currentDraft : input.scratch,
      draft: entries[nextIndex] ?? input.currentDraft,
    };
  }

  if (input.index <= 0) {
    return {
      index: -1,
      scratch: '',
      draft: input.scratch,
    };
  }

  const nextIndex = input.index - 1;
  return {
    index: nextIndex,
    scratch: input.scratch,
    draft: entries[nextIndex] ?? input.scratch,
  };
}
