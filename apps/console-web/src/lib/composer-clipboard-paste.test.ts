import { describe, expect, it } from 'vitest';

import {
  composerAttachmentExtensionLabel,
  composerAttachmentPreviewTitle,
  readClipboardImages,
  readComposerImageFiles,
  readDroppedImages,
  shouldAcceptComposerFileDrop,
  shouldInterceptComposerImagePaste,
} from './composer-clipboard-paste';

describe('composer clipboard paste', () => {
  it('detects pasted image files from clipboard items', () => {
    const file = new File(['pixels'], 'screenshot.png', { type: 'image/png' });
    const event = {
      clipboardData: {
        items: [
          {
            kind: 'file',
            type: 'image/png',
            getAsFile: () => file,
          },
        ],
      },
    } as unknown as ClipboardEvent;

    const images = readClipboardImages(event);
    expect(images).toHaveLength(1);
    expect(images[0]?.name).toBe('screenshot.png');
    expect(images[0]?.mimeType).toBe('image/png');
    expect(shouldInterceptComposerImagePaste(images)).toBe(true);
  });

  it('ignores non-file clipboard items', () => {
    const event = {
      clipboardData: {
        items: [
          {
            kind: 'string',
            type: 'text/plain',
            getAsFile: () => null,
          },
        ],
      },
    } as unknown as ClipboardEvent;

    expect(readClipboardImages(event)).toEqual([]);
  });

  it('reads dropped image files from dataTransfer', () => {
    const file = new File(['pixels'], 'drop.png', { type: 'image/png' });
    const list = {
      0: file,
      length: 1,
      item: (index: number) => (index === 0 ? file : null),
    } as unknown as FileList;
    const event = {
      dataTransfer: { files: list },
    } as unknown as DragEvent;

    const images = readDroppedImages(event);
    expect(images).toHaveLength(1);
    expect(images[0]?.name).toBe('drop.png');
    expect(
      shouldAcceptComposerFileDrop({ dataTransfer: { types: ['Files'] } } as unknown as DragEvent),
    ).toBe(true);
  });

  it('accepts csv and pdf files from the attachment picker path', () => {
    const csv = new File(['a,b\n1,2'], 'report.csv', { type: 'text/csv' });
    const pdf = new File(['%PDF-1.4'], 'brief.pdf', { type: 'application/pdf' });
    const rejected = new File(['MZ'], 'tool.exe', { type: 'application/x-msdownload' });

    const attachments = readComposerImageFiles([csv, pdf, rejected]);
    expect(attachments.map((item) => item.name)).toEqual(['report.csv', 'brief.pdf']);
    expect(attachments[0]?.mimeType).toBe('text/csv');
    expect(attachments[1]?.mimeType).toBe('application/pdf');
    expect(composerAttachmentExtensionLabel('report.csv', 'text/csv')).toBe('CSV');
    expect(composerAttachmentExtensionLabel('brief.pdf', 'application/pdf')).toBe('PDF');
  });

  it('builds preview titles for images and documents', () => {
    expect(composerAttachmentPreviewTitle('screenshot.png', 'image/png')).toBe(
      'Preview screenshot.png',
    );
    expect(composerAttachmentPreviewTitle('report.csv', 'text/csv')).toBe('Open report.csv');
  });

  it('infers csv mime type from filename when browser omits type', () => {
    const csv = new File(['name,value\nx,1'], 'vault.csv', { type: '' });
    const attachments = readComposerImageFiles([csv]);
    expect(attachments).toHaveLength(1);
    expect(attachments[0]?.mimeType).toBe('text/csv');
  });
});
