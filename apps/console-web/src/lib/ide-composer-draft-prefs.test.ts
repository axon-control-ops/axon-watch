import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  draftWasAlreadySubmitted,
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

  it('does not persist or restore drafts without a thread id', () => {
    persistIdeComposerDraft('workspace_a', 'Build the queue UI');
    persistIdeComposerDraft('workspace_b', 'Compare Cursor parity');

    expect(readStoredIdeComposerDraft('workspace_a')).toBe('');
    expect(readStoredIdeComposerDraft('workspace_b')).toBe('');
    expect(readStoredIdeComposerDraft('workspace_c')).toBe('');
  });

  it('isolates drafts per conversation thread', () => {
    persistIdeComposerDraft('workspace_a', 'Sandbox plan draft', 'thread_1');
    persistIdeComposerDraft('workspace_a', 'Worker roster draft', 'thread_2');

    expect(readStoredIdeComposerDraft('workspace_a', 'thread_1')).toBe('Sandbox plan draft');
    expect(readStoredIdeComposerDraft('workspace_a', 'thread_2')).toBe('Worker roster draft');
    expect(readStoredIdeComposerDraft('workspace_a', 'thread_3')).toBe('');
  });

  it('does not migrate legacy workspace drafts into the first thread that reads them', () => {
    window.localStorage.setItem(
      'axon-x-ide-composer-draft-v1',
      JSON.stringify({ workspace_a: 'Legacy shared draft' }),
    );

    expect(readStoredIdeComposerDraft('workspace_a', 'thread_1')).toBe('');
    expect(readStoredIdeComposerDraft('workspace_a', 'thread_2')).toBe('');
    expect(readStoredIdeComposerDraft('workspace_a')).toBe('');
  });

  it('clears stored draft when content is empty', () => {
    persistIdeComposerDraft('workspace_a', 'Temporary draft', 'thread_1');
    persistIdeComposerDraft('workspace_a', '   ', 'thread_1');

    expect(readStoredIdeComposerDraft('workspace_a', 'thread_1')).toBe('');
  });

  it('drops legacy workspace keys when clearing a thread draft', () => {
    window.localStorage.setItem(
      'axon-x-ide-composer-draft-v1',
      JSON.stringify({
        workspace_a: 'Legacy shared draft',
        'workspace_a::thread_1': 'Thread draft',
      }),
    );

    persistIdeComposerDraft('workspace_a', '', 'thread_1');

    const raw = JSON.parse(window.localStorage.getItem('axon-x-ide-composer-draft-v1') ?? '{}') as Record<
      string,
      string
    >;
    expect(raw).toEqual({});
  });

  it('recognizes an already-submitted prompt without deleting a different draft', () => {
    const messages = [
      { role: 'operator', content: 'Count parent responses and uploaded proofs.' },
      { role: 'agent', content: 'I am checking that now.' },
    ];

    expect(
      draftWasAlreadySubmitted(
        '  Count parent responses   and uploaded proofs. ',
        messages,
      ),
    ).toBe(true);
    expect(draftWasAlreadySubmitted('Add a new follow-up request.', messages)).toBe(false);
  });
});
