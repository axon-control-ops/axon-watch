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

  it('persists and restores document attachments per workspace', () => {
    persistComposerAttachments('workspace_a', [
      {
        id: 'composer-file-1',
        name: 'report.csv',
        mimeType: 'text/csv',
        dataUrl: 'data:text/csv;base64,YSxCCjEsMg==',
      },
      {
        id: 'composer-file-2',
        name: 'brief.pdf',
        mimeType: 'application/pdf',
        dataUrl: 'data:application/pdf;base64,JVBERi0xLjQ=',
      },
    ]);

    const restored = readStoredComposerAttachments('workspace_a');
    expect(restored.map((item) => item.name)).toEqual(['report.csv', 'brief.pdf']);

    const csv = composerImageFromStored(restored[0]!);
    expect(csv.mimeType).toBe('text/csv');
    expect(csv.file.type).toBe('text/csv');
    expect(csv.previewUrl.startsWith('data:text/csv')).toBe(true);
  });

  it('isolates attachments per conversation thread', () => {
    persistComposerAttachments(
      'workspace_a',
      [
        {
          id: 'composer-image-1',
          name: 'thread-one.png',
          mimeType: 'image/png',
          dataUrl: 'data:image/png;base64,cGl4ZWxz',
        },
      ],
      'thread_1',
    );
    persistComposerAttachments(
      'workspace_a',
      [
        {
          id: 'composer-image-2',
          name: 'thread-two.png',
          mimeType: 'image/png',
          dataUrl: 'data:image/png;base64,cGl4ZWxz',
        },
      ],
      'thread_2',
    );

    expect(readStoredComposerAttachments('workspace_a', 'thread_1')[0]?.name).toBe('thread-one.png');
    expect(readStoredComposerAttachments('workspace_a', 'thread_2')[0]?.name).toBe('thread-two.png');
    expect(readStoredComposerAttachments('workspace_a', 'thread_3')).toEqual([]);
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
