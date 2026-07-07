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

  it('clears stored draft when content is empty', () => {
    persistIdeComposerDraft('workspace_a', 'Temporary draft');
    persistIdeComposerDraft('workspace_a', '   ');

    expect(readStoredIdeComposerDraft('workspace_a')).toBe('');
  });
});
