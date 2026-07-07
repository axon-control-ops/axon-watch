import { describe, expect, it } from 'vitest';

import {
  readClipboardImages,
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
});
