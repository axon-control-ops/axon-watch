import type { StoredComposerAttachment } from './composer-clipboard-paste';

export type { StoredComposerAttachment };

const IDE_COMPOSER_ATTACHMENTS_KEY = 'axon-x-ide-composer-attachments-v1';

function readStoredComposerAttachmentsByWorkspace(): Record<string, StoredComposerAttachment[]> {
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
    for (const [workspaceId, attachments] of Object.entries(parsed)) {
      const id = workspaceId.trim();
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

export function readStoredComposerAttachments(
  workspaceId: string | null | undefined,
): StoredComposerAttachment[] {
  const id = workspaceId?.trim();
  if (!id) {
    return [];
  }
  return readStoredComposerAttachmentsByWorkspace()[id] ?? [];
}

export function persistComposerAttachments(
  workspaceId: string | null | undefined,
  attachments: StoredComposerAttachment[],
): void {
  if (typeof window === 'undefined') {
    return;
  }

  const id = workspaceId?.trim();
  if (!id) {
    return;
  }

  const current = readStoredComposerAttachmentsByWorkspace();
  if (!attachments.length) {
    const { [id]: _removed, ...rest } = current;
    window.localStorage.setItem(IDE_COMPOSER_ATTACHMENTS_KEY, JSON.stringify(rest));
    return;
  }

  try {
    window.localStorage.setItem(
      IDE_COMPOSER_ATTACHMENTS_KEY,
      JSON.stringify({
        ...current,
        [id]: attachments,
      }),
    );
  } catch {
    // Ignore quota errors — draft text still persists.
  }
}
