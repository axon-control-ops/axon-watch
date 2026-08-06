import { composerThreadScopeKey } from './composer-thread-scope-key';

export type ComposerRuntimePrefs = {
  runtime_target?: string;
  cursor_cli_model?: string;
  codex_cli_model?: string;
  claude_cli_model?: string;
};

type ComposerRuntimePrefsMap = {
  workspaces: Record<string, ComposerRuntimePrefs>;
  updatedAt: string;
};

const STORAGE_KEY = 'axon-watch.composerRuntimePrefs';

type StorageLike = Pick<Storage, 'getItem' | 'setItem'>;

function readMap(storage: StorageLike): ComposerRuntimePrefsMap {
  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) {
      return { workspaces: {}, updatedAt: '' };
    }
    const parsed = JSON.parse(raw) as ComposerRuntimePrefsMap;
    return {
      workspaces:
        parsed?.workspaces && typeof parsed.workspaces === 'object' ? parsed.workspaces : {},
      updatedAt: typeof parsed?.updatedAt === 'string' ? parsed.updatedAt : '',
    };
  } catch {
    return { workspaces: {}, updatedAt: '' };
  }
}

function writeMap(map: ComposerRuntimePrefsMap, storage: StorageLike): void {
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch {
    // Ignore quota or privacy-mode failures.
  }
}

function defaultStorage(): StorageLike {
  return localStorage;
}

/**
 * Read model/runtime prefs for a conversation tab.
 * Thread-scoped when threadId is present; falls back to legacy workspace-only key.
 */
export function readComposerRuntimePrefs(
  workspaceId: string | null,
  threadId?: string | null,
  storage: StorageLike = defaultStorage(),
): ComposerRuntimePrefs {
  if (!workspaceId) {
    return {};
  }
  const map = readMap(storage);
  const threadScope = composerThreadScopeKey(workspaceId, threadId);
  if (threadScope && map.workspaces[threadScope]) {
    return map.workspaces[threadScope];
  }
  // Legacy workspace-wide prefs until the thread writes its own selection.
  return map.workspaces[workspaceId] ?? {};
}

export function writeComposerRuntimePrefs(
  workspaceId: string,
  patch: ComposerRuntimePrefs,
  threadId?: string | null,
  storage: StorageLike = defaultStorage(),
): ComposerRuntimePrefs {
  const map = readMap(storage);
  const scopeKey = composerThreadScopeKey(workspaceId, threadId) ?? workspaceId;
  const current = map.workspaces[scopeKey] ?? map.workspaces[workspaceId] ?? {};
  const next = { ...current, ...patch };
  map.workspaces[scopeKey] = next;
  map.updatedAt = new Date().toISOString();
  writeMap(map, storage);
  return next;
}
