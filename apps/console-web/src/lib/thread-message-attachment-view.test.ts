import { describe, expect, it } from 'vitest';

import {
  isThreadImageAttachment,
  threadAttachmentExtensionLabel,
  threadAttachmentPreviewTitle,
} from './thread-message-attachment-view';
import type { ThreadMessageAttachment } from './operator-thread';

function attachment(
  overrides: Partial<ThreadMessageAttachment> = {},
): ThreadMessageAttachment {
  return {
    attachment_id: 'att-1',
    filename: 'screenshot.png',
    mime_type: 'image/png',
    url: '/api/chat/attachments/att-1',
    ...overrides,
  };
}

describe('thread message attachment view', () => {
  it('detects image attachments by mime type', () => {
    expect(isThreadImageAttachment(attachment())).toBe(true);
    expect(isThreadImageAttachment(attachment({ mime_type: 'IMAGE/JPEG' }))).toBe(true);
    expect(
      isThreadImageAttachment(
        attachment({ filename: 'brief.pdf', mime_type: 'application/pdf' }),
      ),
    ).toBe(false);
  });

  it('builds preview titles for images and documents', () => {
    expect(threadAttachmentPreviewTitle(attachment())).toBe('Preview screenshot.png');
    expect(
      threadAttachmentPreviewTitle(
        attachment({ filename: 'report.csv', mime_type: 'text/csv' }),
      ),
    ).toBe('Open report.csv');
  });

  it('derives extension badges from filename and mime type', () => {
    expect(
      threadAttachmentExtensionLabel(
        attachment({ filename: 'report.csv', mime_type: 'text/csv' }),
      ),
    ).toBe('CSV');
    expect(
      threadAttachmentExtensionLabel(
        attachment({ filename: 'brief.pdf', mime_type: 'application/pdf' }),
      ),
    ).toBe('PDF');
  });
});
