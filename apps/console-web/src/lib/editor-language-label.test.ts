import { describe, expect, it } from 'vitest';

import { buildEditorLanguageLabel } from './editor-language-label';

describe('buildEditorLanguageLabel', () => {
  it('labels agent diff reviews distinctly from markdown reviews', () => {
    expect(
      buildEditorLanguageLabel({
        language: 'typescript',
        isAgentEditReview: true,
        isMarkdownEditorDocument: false,
      }),
    ).toBe('Diff review');
    expect(
      buildEditorLanguageLabel({
        language: 'markdown',
        isAgentEditReview: true,
        isMarkdownEditorDocument: true,
      }),
    ).toBe('Markdown review');
  });

  it('maps known editor languages and falls back to the raw id', () => {
    expect(
      buildEditorLanguageLabel({
        language: 'python',
        isAgentEditReview: false,
        isMarkdownEditorDocument: false,
      }),
    ).toBe('Python');
    expect(
      buildEditorLanguageLabel({
        language: 'yaml',
        isAgentEditReview: false,
        isMarkdownEditorDocument: false,
      }),
    ).toBe('YAML');
  });

  it('labels Vue SFCs distinctly from generic HTML', () => {
    expect(
      buildEditorLanguageLabel({
        language: 'html',
        filePath: 'apps/console-web/src/App.vue',
        isAgentEditReview: false,
        isMarkdownEditorDocument: false,
      }),
    ).toBe('Vue');
    expect(
      buildEditorLanguageLabel({
        language: 'html',
        filePath: 'apps/console-web/index.html',
        isAgentEditReview: false,
        isMarkdownEditorDocument: false,
      }),
    ).toBe('HTML');
  });

  it('labels TSX, JSX, and MDX paths distinctly from plain TypeScript, JavaScript, and Markdown', () => {
    expect(
      buildEditorLanguageLabel({
        language: 'typescript',
        filePath: 'apps/console-web/src/composables/useIdeEditorStatusBar.ts',
        isAgentEditReview: false,
        isMarkdownEditorDocument: false,
      }),
    ).toBe('TypeScript');
    expect(
      buildEditorLanguageLabel({
        language: 'typescript',
        filePath: 'apps/console-web/src/components/Button.tsx',
        isAgentEditReview: false,
        isMarkdownEditorDocument: false,
      }),
    ).toBe('TSX');
    expect(
      buildEditorLanguageLabel({
        language: 'javascript',
        filePath: 'apps/console-web/src/legacy/Widget.jsx',
        isAgentEditReview: false,
        isMarkdownEditorDocument: false,
      }),
    ).toBe('JSX');
    expect(
      buildEditorLanguageLabel({
        language: 'markdown',
        filePath: 'docs/guide.mdx',
        isAgentEditReview: false,
        isMarkdownEditorDocument: false,
      }),
    ).toBe('MDX');
  });

  it('labels common config paths even when Monaco uses a generic language id', () => {
    expect(
      buildEditorLanguageLabel({
        language: 'plaintext',
        filePath: 'pyproject.toml',
        isAgentEditReview: false,
        isMarkdownEditorDocument: false,
      }),
    ).toBe('TOML');
    expect(
      buildEditorLanguageLabel({
        language: 'css',
        filePath: 'apps/console-web/src/styles/theme.scss',
        isAgentEditReview: false,
        isMarkdownEditorDocument: false,
      }),
    ).toBe('SCSS');
    expect(
      buildEditorLanguageLabel({
        language: 'plaintext',
        filePath: 'config/workspaces.yaml',
        isAgentEditReview: false,
        isMarkdownEditorDocument: false,
      }),
    ).toBe('YAML');
  });
});
