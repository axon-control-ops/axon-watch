import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  persistIdeComposerDraft,
  readStoredIdeComposerDraft,
} from './ide-composer-draft-prefs';

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

describe('ide composer draft prefs', () => {
  beforeEach(() => {
    vi.stubGlobal('window', { localStorage: new MemoryStorage() });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('persists and restores drafts per workspace', () => {
    persistIdeComposerDraft('workspace_a', 'Build the queue UI');
    persistIdeComposerDraft('workspace_b', 'Compare Cursor parity');

    expect(readStoredIdeComposerDraft('workspace_a')).toBe('Build the queue UI');
    expect(readStoredIdeComposerDraft('workspace_b')).toBe('Compare Cursor parity');
    expect(readStoredIdeComposerDraft('workspace_c')).toBe('');
  });

  it('isolates drafts per conversation thread', () => {
    persistIdeComposerDraft('workspace_a', 'Sandbox plan draft', 'thread_1');
    persistIdeComposerDraft('workspace_a', 'Worker roster draft', 'thread_2');

    expect(readStoredIdeComposerDraft('workspace_a', 'thread_1')).toBe('Sandbox plan draft');
    expect(readStoredIdeComposerDraft('workspace_a', 'thread_2')).toBe('Worker roster draft');
    expect(readStoredIdeComposerDraft('workspace_a', 'thread_3')).toBe('');
  });

  it('migrates legacy workspace drafts into the first thread that reads them', () => {
    persistIdeComposerDraft('workspace_a', 'Legacy shared draft');

    expect(readStoredIdeComposerDraft('workspace_a', 'thread_1')).toBe('Legacy shared draft');
    expect(readStoredIdeComposerDraft('workspace_a', 'thread_2')).toBe('');
    expect(readStoredIdeComposerDraft('workspace_a')).toBe('');
  });

  it('clears stored draft when content is empty', () => {
    persistIdeComposerDraft('workspace_a', 'Temporary draft', 'thread_1');
    persistIdeComposerDraft('workspace_a', '   ', 'thread_1');

    expect(readStoredIdeComposerDraft('workspace_a', 'thread_1')).toBe('');
  });
});
