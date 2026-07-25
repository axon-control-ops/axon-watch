import {
  composerAttachmentExtensionLabel,
  composerAttachmentPreviewTitle,
} from './composer-clipboard-paste';
import type { ThreadMessageAttachment } from './operator-thread';

/** Whether a persisted thread attachment should render as an inline image preview. */
export function isThreadImageAttachment(attachment: ThreadMessageAttachment): boolean {
  return attachment.mime_type.trim().toLowerCase().startsWith('image/');
}

/** Tooltip for a thread attachment preview/open button. */
export function threadAttachmentPreviewTitle(attachment: ThreadMessageAttachment): string {
  return composerAttachmentPreviewTitle(attachment.filename, attachment.mime_type);
}

/** Short extension badge for non-image thread attachments. */
export function threadAttachmentExtensionLabel(attachment: ThreadMessageAttachment): string {
  return composerAttachmentExtensionLabel(attachment.filename, attachment.mime_type);
}
