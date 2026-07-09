import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest';

import {
  OPEN_EDITOR_FILE_TABS_KEY,
  ACTIVE_EDITOR_DOCUMENT_IDS_KEY,
  readOpenEditorFilePathsByWorkspace,
  writeOpenEditorFilePathsForWorkspace,
  readActiveEditorDocumentIdsByWorkspace,
  writeActiveEditorDocumentIdForWorkspace,
  restoreOpenEditorFilePaths,
  resolveRestoredActiveEditorDocumentId,
} from './editor-open-tabs-prefs';

class MemoryStorage {
  private data = new Map<string, string>();

  getItem(key: string): string | null {
    return this.data.has(key) ? (this.data.get(key) as string) : null;
  }

  setItem(key: string, value: string): void {
    this.data.set(key, String(value));
  }

  removeItem(key: string): void {
    this.data.delete(key);
  }
}

describe('editor-open-tabs-prefs', () => {
  beforeEach(() => {
    vi.stubGlobal('window', { localStorage: new MemoryStorage() });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('persists open file tabs per workspace', () => {
    writeOpenEditorFilePathsForWorkspace('workspace_dashpro', [
      'README.md',
      'app/index.ts',
      '../evil.ts',
      'README.md',
    ]);
    expect(readOpenEditorFilePathsByWorkspace()).toEqual({
      workspace_dashpro: ['README.md', 'app/index.ts'],
    });
    expect(window.localStorage.getItem(OPEN_EDITOR_FILE_TABS_KEY)).toContain('README.md');
  });

  it('persists active editor document ids per workspace', () => {
    writeActiveEditorDocumentIdForWorkspace('workspace_dashpro', 'file:app/index.ts');
    expect(readActiveEditorDocumentIdsByWorkspace()).toEqual({
      workspace_dashpro: 'file:app/index.ts',
    });
    expect(window.localStorage.getItem(ACTIVE_EDITOR_DOCUMENT_IDS_KEY)).toContain('app/index.ts');
  });

  it('restores only paths that still exist', () => {
    expect(
      restoreOpenEditorFilePaths(
        ['README.md', 'gone.ts', 'src/main.ts'],
        ['README.md', 'src/main.ts', 'package.json'],
        'package.json',
      ),
    ).toEqual(['README.md', 'src/main.ts']);
  });

  it('falls back when stored tabs are empty or missing', () => {
    expect(
      restoreOpenEditorFilePaths([], ['README.md', 'src/main.ts'], 'README.md'),
    ).toEqual(['README.md']);
  });

  it('resolves active document to an open file tab', () => {
    expect(
      resolveRestoredActiveEditorDocumentId({
        storedDocumentId: 'file:src/main.ts',
        openedPaths: ['README.md', 'src/main.ts'],
      }),
    ).toBe('file:src/main.ts');
    expect(
      resolveRestoredActiveEditorDocumentId({
        storedDocumentId: 'file:gone.ts',
        openedPaths: ['README.md', 'src/main.ts'],
      }),
    ).toBe('file:README.md');
  });
});
