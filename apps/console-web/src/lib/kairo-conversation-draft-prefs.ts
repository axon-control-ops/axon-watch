const KAIRO_CONVERSATION_DRAFT_KEY = 'axon-x-kairo-conversation-draft-v1';

function readStoredKairoDraftByWorkspace(): Record<string, string> {
  if (typeof window === 'undefined') {
    return {};
  }

  try {
    const raw = window.localStorage.getItem(KAIRO_CONVERSATION_DRAFT_KEY);
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

function writeStoredKairoDraftByWorkspace(map: Record<string, string>): void {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(KAIRO_CONVERSATION_DRAFT_KEY, JSON.stringify(map));
}

export function readStoredKairoConversationDraft(
  workspaceId: string | null | undefined,
): string {
  const workspace = String(workspaceId ?? '').trim();
  if (!workspace) {
    return '';
  }
  return readStoredKairoDraftByWorkspace()[workspace] ?? '';
}

export function persistKairoConversationDraft(
  workspaceId: string | null | undefined,
  draft: string,
): void {
  if (typeof window === 'undefined') {
    return;
  }

  const workspace = String(workspaceId ?? '').trim();
  if (!workspace) {
    return;
  }

  const current = readStoredKairoDraftByWorkspace();
  if (!draft.trim()) {
    const { [workspace]: _removed, ...rest } = current;
    writeStoredKairoDraftByWorkspace(rest);
    return;
  }

  writeStoredKairoDraftByWorkspace({
    ...current,
    [workspace]: draft,
  });
}
