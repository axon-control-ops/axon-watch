import { describe, expect, it } from 'vitest';

import { languageForFilePath, workspaceFileDocumentId } from './workspace-file-language';

describe('workspace-file-language', () => {
  it('maps markdown extension to markdown language', () => {
    expect(languageForFilePath('README.md')).toBe('markdown');
  });

  it('builds stable file document ids', () => {
    expect(workspaceFileDocumentId('notes.txt')).toBe('file:notes.txt');
  });
});
