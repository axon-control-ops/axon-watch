import { describe, expect, it } from 'vitest';

import { languageForFilePath, workspaceFileDocumentId } from './workspace-file-language';

describe('workspace-file-language', () => {
  it('maps markdown extension to markdown language', () => {
    expect(languageForFilePath('README.md')).toBe('markdown');
  });

  it('maps vue to html highlighting (not typescript)', () => {
    expect(languageForFilePath('components/BottomPanel.vue')).toBe('html');
  });

  it('maps css and tsx extensions', () => {
    expect(languageForFilePath('styles/app.css')).toBe('css');
    expect(languageForFilePath('Button.tsx')).toBe('typescript');
  });

  it('builds stable file document ids', () => {
    expect(workspaceFileDocumentId('notes.txt')).toBe('file:notes.txt');
  });
});
