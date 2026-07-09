import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { composerImageFromStored } from './composer-clipboard-paste';
import {
  persistComposerAttachments,
  readStoredComposerAttachments,
} from './ide-composer-attachment-prefs';

class MemoryStorage {
  private store = new Map<string, string>();

  getItem(key: string): string | null {
    return this.store.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.store.set(key, value);
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }

  clear(): void {
    this.store.clear();
  }
}

describe('ide composer attachment prefs', () => {
  beforeEach(() => {
    vi.stubGlobal('window', { localStorage: new MemoryStorage() });
    vi.stubGlobal('atob', (value: string) => Buffer.from(value, 'base64').toString('binary'));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('persists and restores image attachments per workspace', () => {
    persistComposerAttachments('workspace_a', [
      {
        id: 'composer-image-1',
        name: 'screenshot.png',
        mimeType: 'image/png',
        dataUrl: 'data:image/png;base64,cGl4ZWxz',
      },
    ]);

    const restored = readStoredComposerAttachments('workspace_a');
    expect(restored).toHaveLength(1);
    expect(restored[0]?.name).toBe('screenshot.png');

    const roundTrip = composerImageFromStored(restored[0]!);
    expect(roundTrip.name).toBe('screenshot.png');
    expect(roundTrip.file.type).toBe('image/png');
    expect(roundTrip.previewUrl.startsWith('data:image/png')).toBe(true);
  });

  it('clears stored attachments when list is empty', () => {
    persistComposerAttachments('workspace_a', [
      {
        id: 'composer-image-1',
        name: 'screenshot.png',
        mimeType: 'image/png',
        dataUrl: 'data:image/png;base64,cGl4ZWxz',
      },
    ]);
    persistComposerAttachments('workspace_a', []);

    expect(readStoredComposerAttachments('workspace_a')).toEqual([]);
  });
});
