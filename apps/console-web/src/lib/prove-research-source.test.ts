import { describe, expect, it } from 'vitest';
import {
  buildResearchEditorContent,
  researchBlockPreview,
  shouldOpenResearchInEditor,
} from './prove-research-source';

describe('prove-research-source', () => {
  it('builds editor markdown with citation footer', () => {
    expect(
      buildResearchEditorContent('Docs', 'https://example.com/docs', 'Hello world'),
    ).toContain('Hello world');
    expect(
      buildResearchEditorContent('Docs', 'https://example.com/docs', 'Hello world'),
    ).toContain('[Docs](https://example.com/docs)');
  });

  it('opens fetch snippets in editor only for fetch blocks', () => {
    expect(shouldOpenResearchInEditor('fetch', 'Page body')).toBe(true);
    expect(shouldOpenResearchInEditor('search', 'Result snippet')).toBe(false);
  });

  it('summarizes research blocks for collapsed headers', () => {
    expect(
      researchBlockPreview({
        query: 'vite config',
        kind: 'search',
        provider: 'duckduckgo_instant',
        items: [
          { title: 'Vite', url: 'https://vitejs.dev/', snippet: 'Docs' },
          { title: 'Rollup', url: 'https://rollupjs.org/', snippet: 'Bundler' },
        ],
      }),
    ).toContain('Web search');
    expect(
      researchBlockPreview({
        query: 'vite config',
        kind: 'search',
        provider: 'duckduckgo_instant',
        items: [
          { title: 'Vite', url: 'https://vitejs.dev/', snippet: 'Docs' },
          { title: 'Rollup', url: 'https://rollupjs.org/', snippet: 'Bundler' },
        ],
      }),
    ).toContain('2 sources');
    expect(
      researchBlockPreview({
        query: 'Page fetch',
        kind: 'fetch',
        items: [{ title: 'Example', url: 'https://example.com/', snippet: 'Body' }],
        live: true,
      }),
    ).toBe('Page fetch');
  });
});
