import { describe, expect, it } from 'vitest';

import {
  isImageFilePath,
  isPdfFilePath,
  languageForFilePath,
  workspaceFileDocumentId,
} from './workspace-file-language';

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

  it('maps csv and yaml extensions', () => {
    expect(languageForFilePath('reports/july.csv')).toBe('csv');
    expect(languageForFilePath('config/app.yaml')).toBe('yaml');
  });

  it('detects image and pdf canvas paths', () => {
    expect(isImageFilePath('output/signs/young-eagles-parent-gate-sign.svg')).toBe(true);
    expect(isPdfFilePath('output/signs/young-eagles-parent-gate-sign.pdf')).toBe(true);
    expect(isPdfFilePath('src/app.ts')).toBe(false);
  });

  it('builds stable file document ids', () => {
    expect(workspaceFileDocumentId('notes.txt')).toBe('file:notes.txt');
  });
});
