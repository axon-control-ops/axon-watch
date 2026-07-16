import type { StoredComposerAttachment } from './composer-clipboard-paste';
import { composerThreadScopeKey } from './composer-thread-scope-key';

export type { StoredComposerAttachment };

const IDE_COMPOSER_ATTACHMENTS_KEY = 'axon-x-ide-composer-attachments-v1';

function readStoredComposerAttachmentsByScope(): Record<string, StoredComposerAttachment[]> {
  if (typeof window === 'undefined') {
    return {};
  }

  try {
    const raw = window.localStorage.getItem(IDE_COMPOSER_ATTACHMENTS_KEY);
    if (!raw) {
      return {};
    }

    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return {};
    }

    const output: Record<string, StoredComposerAttachment[]> = {};
    for (const [scopeKey, attachments] of Object.entries(parsed)) {
      const id = scopeKey.trim();
      if (!id || !Array.isArray(attachments)) {
        continue;
      }

      const normalized: StoredComposerAttachment[] = [];
      for (const attachment of attachments) {
        if (!attachment || typeof attachment !== 'object' || Array.isArray(attachment)) {
          continue;
        }
        const record = attachment as Partial<StoredComposerAttachment>;
        const attachmentId = record.id?.trim();
        const name = record.name?.trim();
        const mimeType = record.mimeType?.trim();
        const dataUrl = record.dataUrl?.trim();
        if (!attachmentId || !name || !mimeType || !dataUrl?.startsWith('data:')) {
          continue;
        }
        normalized.push({
          id: attachmentId,
          name,
          mimeType,
          dataUrl,
        });
      }

      if (normalized.length) {
        output[id] = normalized;
      }
    }
    return output;
  } catch {
    return {};
  }
}

function writeStoredComposerAttachmentsByScope(
  map: Record<string, StoredComposerAttachment[]>,
): void {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.localStorage.setItem(IDE_COMPOSER_ATTACHMENTS_KEY, JSON.stringify(map));
  } catch {
    // Ignore quota errors — draft text still persists.
  }
}

function resolveAttachmentScopeKey(
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

export function readStoredComposerAttachments(
  workspaceId: string | null | undefined,
  threadId?: string | null,
): StoredComposerAttachment[] {
  const map = readStoredComposerAttachmentsByScope();
  const threadScope = composerThreadScopeKey(workspaceId, threadId);
  if (threadScope) {
    if (Object.prototype.hasOwnProperty.call(map, threadScope)) {
      return map[threadScope] ?? [];
    }
    const workspace = String(workspaceId ?? '').trim();
    if (workspace && Object.prototype.hasOwnProperty.call(map, workspace)) {
      const legacy = map[workspace] ?? [];
      const { [workspace]: _removed, ...rest } = map;
      if (legacy.length) {
        writeStoredComposerAttachmentsByScope({ ...rest, [threadScope]: legacy });
        return legacy;
      }
      writeStoredComposerAttachmentsByScope(rest);
    }
    return [];
  }

  const scopeKey = resolveAttachmentScopeKey(workspaceId, null);
  if (!scopeKey) {
    return [];
  }
  return map[scopeKey] ?? [];
}

export function persistComposerAttachments(
  workspaceId: string | null | undefined,
  attachments: StoredComposerAttachment[],
  threadId?: string | null,
): void {
  if (typeof window === 'undefined') {
    return;
  }

  const scopeKey = resolveAttachmentScopeKey(workspaceId, threadId);
  if (!scopeKey) {
    return;
  }

  const current = readStoredComposerAttachmentsByScope();
  if (!attachments.length) {
    const { [scopeKey]: _removed, ...rest } = current;
    writeStoredComposerAttachmentsByScope(rest);
    return;
  }

  writeStoredComposerAttachmentsByScope({
    ...current,
    [scopeKey]: attachments,
  });
}
