import type { ComposerClipboardImage } from '../../lib/composer-clipboard-paste';
import { uploadChatAttachment } from '../../api/chat-api';

/** Upload pending VAXON bar files and return attachment_ids for /api/kairo/converse. */
export async function uploadVaxonConverseAttachments(
  workspaceId: string,
  attachments: readonly ComposerClipboardImage[],
): Promise<string[]> {
  const ids: string[] = [];
  for (const item of attachments) {
    const record = await uploadChatAttachment(workspaceId, item.file);
    const id = String(record.attachment_id || '').trim();
    if (id) {
      ids.push(id);
    }
  }
  return ids;
}

export function vaxonConversePromptForAttachments(
  draft: string,
  attachmentCount: number,
): string {
  const trimmed = draft.trim();
  if (trimmed) {
    return trimmed;
  }
  if (attachmentCount > 0) {
    return 'Please review the attached files.';
  }
  return '';
}
