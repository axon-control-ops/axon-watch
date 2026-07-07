import { describe, expect, it } from 'vitest';
import { canFlyToWorkspaceSource, resolveResearchFlyToTarget } from './research-fly-to-source';

describe('research-fly-to-source', () => {
  it('resolves workspace file paths with line numbers from snippets', () => {
    expect(
      resolveResearchFlyToTarget({
        title: 'Config',
        url: 'about:blank',
        snippet: 'See apps/console-web/src/lib/foo.ts:42 for details',
        query: 'vite config',
      }),
    ).toEqual({
      path: 'apps/console-web/src/lib/foo.ts',
      line: 42,
      searchText: 'vite config',
    });
  });

  it('resolves file:// urls', () => {
    expect(
      resolveResearchFlyToTarget({
        title: 'Readme',
        url: 'file:///README.md#L3',
        snippet: '',
      }),
    ).toEqual({
      path: 'README.md',
      line: 3,
    });
  });

  it('returns null for external http sources', () => {
    expect(
      canFlyToWorkspaceSource({
        title: 'Vite',
        url: 'https://vitejs.dev/',
        snippet: 'Official docs',
      }),
    ).toBe(false);
  });
});
