import { describe, expect, it } from 'vitest';

import {
  readClipboardImages,
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

  it('ignores non-image clipboard items', () => {
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
});
