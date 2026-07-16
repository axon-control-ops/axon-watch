import { composerThreadScopeKey } from './composer-thread-scope-key';

const IDE_COMPOSER_DRAFT_KEY = 'axon-x-ide-composer-draft-v1';

function readStoredIdeComposerDraftByScope(): Record<string, string> {
  if (typeof window === 'undefined') {
    return {};
  }

  try {
    const raw = window.localStorage.getItem(IDE_COMPOSER_DRAFT_KEY);
    if (!raw) {
      return {};
    }

    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return {};
    }

    const output: Record<string, string> = {};
    for (const [scopeKey, draft] of Object.entries(parsed)) {
      const id = scopeKey.trim();
      if (!id || typeof draft !== 'string') {
        continue;
      }
      output[id] = draft;
    }
    return output;
  } catch {
    return {};
  }
}

function writeStoredIdeComposerDraftByScope(map: Record<string, string>): void {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(IDE_COMPOSER_DRAFT_KEY, JSON.stringify(map));
}

function resolveDraftScopeKey(
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
 * Read composer draft for a conversation tab.
 * Prefer thread-scoped keys; migrate a one-time legacy workspace draft when present.
 */
export function readStoredIdeComposerDraft(
  workspaceId: string | null | undefined,
  threadId?: string | null,
): string {
  const map = readStoredIdeComposerDraftByScope();
  const threadScope = composerThreadScopeKey(workspaceId, threadId);
  if (threadScope) {
    if (Object.prototype.hasOwnProperty.call(map, threadScope)) {
      return map[threadScope] ?? '';
    }
    // One-time migration from pre-isolation workspace-only drafts.
    const workspace = String(workspaceId ?? '').trim();
    if (workspace && Object.prototype.hasOwnProperty.call(map, workspace)) {
      const legacy = map[workspace] ?? '';
      const { [workspace]: _removed, ...rest } = map;
      if (legacy.trim()) {
        writeStoredIdeComposerDraftByScope({ ...rest, [threadScope]: legacy });
        return legacy;
      }
      writeStoredIdeComposerDraftByScope(rest);
    }
    return '';
  }

  const workspaceScope = resolveDraftScopeKey(workspaceId, null);
  if (!workspaceScope) {
    return '';
  }
  return map[workspaceScope] ?? '';
}

export function persistIdeComposerDraft(
  workspaceId: string | null | undefined,
  draft: string,
  threadId?: string | null,
): void {
  if (typeof window === 'undefined') {
    return;
  }

  const scopeKey = resolveDraftScopeKey(workspaceId, threadId);
  if (!scopeKey) {
    return;
  }

  const current = readStoredIdeComposerDraftByScope();
  if (!draft.trim()) {
    const { [scopeKey]: _removed, ...rest } = current;
    writeStoredIdeComposerDraftByScope(rest);
    return;
  }

  writeStoredIdeComposerDraftByScope({
    ...current,
    [scopeKey]: draft,
  });
}
