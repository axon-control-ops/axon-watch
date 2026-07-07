const IDE_COMPOSER_DRAFT_KEY = 'axon-x-ide-composer-draft-v1';

function readStoredIdeComposerDraftByWorkspace(): Record<string, string> {
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
    for (const [workspaceId, draft] of Object.entries(parsed)) {
      const id = workspaceId.trim();
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

export function readStoredIdeComposerDraft(workspaceId: string | null | undefined): string {
  const id = workspaceId?.trim();
  if (!id) {
    return '';
  }
  return readStoredIdeComposerDraftByWorkspace()[id] ?? '';
}

export function persistIdeComposerDraft(
  workspaceId: string | null | undefined,
  draft: string,
): void {
  if (typeof window === 'undefined') {
    return;
  }

  const id = workspaceId?.trim();
  if (!id) {
    return;
  }

  const current = readStoredIdeComposerDraftByWorkspace();
  if (!draft.trim()) {
    const { [id]: _removed, ...rest } = current;
    window.localStorage.setItem(IDE_COMPOSER_DRAFT_KEY, JSON.stringify(rest));
    return;
  }

  window.localStorage.setItem(
    IDE_COMPOSER_DRAFT_KEY,
    JSON.stringify({
      ...current,
      [id]: draft,
    }),
  );
}
