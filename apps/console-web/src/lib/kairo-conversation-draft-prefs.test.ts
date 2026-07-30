import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  persistKairoConversationDraft,
  readStoredKairoConversationDraft,
} from './kairo-conversation-draft-prefs';

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

describe('kairo conversation draft prefs', () => {
  beforeEach(() => {
    vi.stubGlobal('window', { localStorage: new MemoryStorage() });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('persists and restores drafts per workspace', () => {
    persistKairoConversationDraft('workspace_a', 'Ask about fleet health');
    persistKairoConversationDraft('workspace_b', 'Dispatch a briefing');

    expect(readStoredKairoConversationDraft('workspace_a')).toBe('Ask about fleet health');
    expect(readStoredKairoConversationDraft('workspace_b')).toBe('Dispatch a briefing');
    expect(readStoredKairoConversationDraft('workspace_c')).toBe('');
  });

  it('clears empty drafts from storage', () => {
    persistKairoConversationDraft('workspace_a', 'Temporary draft');
    persistKairoConversationDraft('workspace_a', '   ');

    expect(readStoredKairoConversationDraft('workspace_a')).toBe('');
  });
});
