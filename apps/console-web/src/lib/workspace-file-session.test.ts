import { describe, expect, it } from 'vitest';

import {
  buildOpenedFileDocuments,
  isSafeWorkspaceFilePath,
  normalizeWorkspaceFilePath,
  remapWorkspaceFilePaths,
  remapWorkspaceFileRecord,
} from './workspace-file-session';

describe('workspace file session helpers', () => {
  it('normalizes entered workspace file paths', () => {
    expect(normalizeWorkspaceFilePath(' /src//notes.md ')).toBe('src/notes.md');
  });

  it('rejects traversal paths', () => {
    expect(isSafeWorkspaceFilePath('src/notes.md')).toBe(true);
    expect(isSafeWorkspaceFilePath('../notes.md')).toBe(false);
  });

  it('remaps record keys after rename', () => {
    expect(
      remapWorkspaceFileRecord(
        { 'src/old.txt': 'hello', 'src/keep.txt': 'keep' },
        'src/old.txt',
        'src/new.txt',
      ),
    ).toEqual({
      'src/new.txt': 'hello',
      'src/keep.txt': 'keep',
    });
  });

  it('remaps opened paths after rename', () => {
    expect(
      remapWorkspaceFilePaths(['README.md', 'src/old.txt'], 'src/old.txt', 'src/new.txt'),
    ).toEqual(['README.md', 'src/new.txt']);
  });

  it('builds image tabs before the workspace file index catches up', () => {
    const documents = buildOpenedFileDocuments(
      [{ path: 'README.md', size_bytes: 12 }],
      ['assets/mockup.png'],
      {},
      {},
      { 'assets/mockup.png': 'loaded' },
    );

    expect(documents).toEqual([
      expect.objectContaining({
        filePath: 'assets/mockup.png',
        language: 'image',
        readOnly: true,
      }),
    ]);
  });
});
