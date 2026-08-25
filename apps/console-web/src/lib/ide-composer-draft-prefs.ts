import { composerThreadScopeKey } from './composer-thread-scope-key';

const IDE_COMPOSER_DRAFT_KEY = 'axon-x-ide-composer-draft-v1';

function normalizedDraftText(value: string | null | undefined): string {
  return String(value ?? '').trim().replace(/\s+/g, ' ');
}

export function draftWasAlreadySubmitted(
  draft: string | null | undefined,
  messages: ReadonlyArray<{ role?: string | null; content?: string | null }>,
): boolean {
  const candidate = normalizedDraftText(draft);
  if (!candidate) {
    return false;
  }
  return messages.some(
    (message) =>
      message.role === 'operator'
      && normalizedDraftText(message.content) === candidate,
  );
}

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

/**
 * Read composer draft for a conversation tab.
 * Thread-scoped only — never migrate workspace-wide drafts into an arbitrary tab
 * (that leaked prompts across employees / workspaces).
 */
export function readStoredIdeComposerDraft(
  workspaceId: string | null | undefined,
  threadId?: string | null,
): string {
  const threadScope = composerThreadScopeKey(workspaceId, threadId);
  if (!threadScope) {
    return '';
  }
  const map = readStoredIdeComposerDraftByScope();
  return map[threadScope] ?? '';
}

/**
 * Persist composer draft for a conversation tab.
 * Requires a thread id — workspace-only keys are no longer written.
 */
export function persistIdeComposerDraft(
  workspaceId: string | null | undefined,
  draft: string,
  threadId?: string | null,
): void {
  if (typeof window === 'undefined') {
    return;
  }

  const scopeKey = composerThreadScopeKey(workspaceId, threadId);
  if (!scopeKey) {
    return;
  }

  const current = readStoredIdeComposerDraftByScope();
  if (!draft.trim()) {
    const { [scopeKey]: _removed, ...rest } = current;
    // Drop legacy workspace-only keys for this workspace when clearing a thread.
    const workspace = String(workspaceId ?? '').trim();
    const withoutLegacy =
      workspace && Object.prototype.hasOwnProperty.call(rest, workspace)
        ? (() => {
            const { [workspace]: _legacy, ...kept } = rest;
            return kept;
          })()
        : rest;
    writeStoredIdeComposerDraftByScope(withoutLegacy);
    return;
  }

  writeStoredIdeComposerDraftByScope({
    ...current,
    [scopeKey]: draft,
  });
}
