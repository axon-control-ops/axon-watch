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

function resolveModeScopeKey(
  workspaceId: string | null | undefined,
  threadId?: string | null,
): string | null {
  const threadScope = composerThreadScopeKey(workspaceId, threadId);
  if (threadScope) {
    return threadScope;
  }
  const workspace = String(workspaceId ?? '').trim();
  return workspace || null;
}

/**
 * Read composer mode for a conversation tab.
 * Thread-scoped first; migrates legacy workspace mode once when needed.
 */
export function readWorkspaceComposerMode(
  workspaceId: string | null | undefined,
  storage: Pick<Storage, 'getItem' | 'setItem'> = sessionStorage,
  threadId?: string | null,
): StoredComposerMode | null {
  const map = readMap(storage);
  const threadScope = composerThreadScopeKey(workspaceId, threadId);
  if (threadScope) {
    if (Object.prototype.hasOwnProperty.call(map, threadScope)) {
      return map[threadScope] ?? null;
    }
    const workspace = String(workspaceId ?? '').trim();
    if (workspace && Object.prototype.hasOwnProperty.call(map, workspace)) {
      const legacy = map[workspace] ?? null;
      if (legacy) {
        const { [workspace]: _removed, ...rest } = map;
        storage.setItem(
          COMPOSER_MODE_KEY,
          JSON.stringify({ ...rest, [threadScope]: legacy }),
        );
        return legacy;
      }
    }
    return null;
  }

  const key = resolveModeScopeKey(workspaceId, null);
  return key ? map[key] ?? null : null;
}

export function persistWorkspaceComposerMode(
  workspaceId: string | null | undefined,
  mode: StoredComposerMode,
  storage: Pick<Storage, 'getItem' | 'setItem'> = sessionStorage,
  threadId?: string | null,
): void {
  const key = resolveModeScopeKey(workspaceId, threadId);
  if (!key || !VALID_MODES.has(mode)) {
    return;
  }
  storage.setItem(COMPOSER_MODE_KEY, JSON.stringify({ ...readMap(storage), [key]: mode }));
}
