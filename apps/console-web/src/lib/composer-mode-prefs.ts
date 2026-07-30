import { composerThreadScopeKey } from './composer-thread-scope-key';

export type StoredComposerMode = 'agent' | 'plan' | 'ask' | 'debug' | 'kairo';

const COMPOSER_MODE_KEY = 'axon-x:ide-composer-mode-by-workspace:v2';
const VALID_MODES = new Set<StoredComposerMode>(['agent', 'plan', 'ask', 'debug', 'kairo']);

function readMap(storage: Pick<Storage, 'getItem'>): Record<string, StoredComposerMode> {
  try {
    const parsed = JSON.parse(storage.getItem(COMPOSER_MODE_KEY) ?? '{}') as Record<string, unknown>;
    return Object.fromEntries(
      Object.entries(parsed).filter(
        (entry): entry is [string, StoredComposerMode] =>
          Boolean(entry[0]) && VALID_MODES.has(entry[1] as StoredComposerMode),
      ),
    );
  } catch {
    return {};
  }
}

/**
 * Read composer mode for a conversation tab.
 * Thread-scoped only — do not migrate workspace-wide modes into an arbitrary tab.
 */
export function readWorkspaceComposerMode(
  workspaceId: string | null | undefined,
  storage: Pick<Storage, 'getItem' | 'setItem'> = sessionStorage,
  threadId?: string | null,
): StoredComposerMode | null {
  const map = readMap(storage);
  const threadScope = composerThreadScopeKey(workspaceId, threadId);
  if (!threadScope) {
    return null;
  }
  return map[threadScope] ?? null;
}

export function persistWorkspaceComposerMode(
  workspaceId: string | null | undefined,
  mode: StoredComposerMode,
  storage: Pick<Storage, 'getItem' | 'setItem'> = sessionStorage,
  threadId?: string | null,
): void {
  const key = composerThreadScopeKey(workspaceId, threadId);
  if (!key || !VALID_MODES.has(mode)) {
    return;
  }
  storage.setItem(COMPOSER_MODE_KEY, JSON.stringify({ ...readMap(storage), [key]: mode }));
}
