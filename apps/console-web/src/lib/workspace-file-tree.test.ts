import { describe, expect, it } from 'vitest';

import {
  buildCollapsedDirectoryState,
  buildExpandedDirectoryState,
  buildWorkspaceFileTree,
  collectDirectoryPaths,
} from './workspace-file-tree';

describe('buildWorkspaceFileTree', () => {
  it('groups nested paths into directories', () => {
    const tree = buildWorkspaceFileTree([
      { path: 'README.md', size_bytes: 12 },
      { path: 'src/lib/util.ts', size_bytes: 40 },
      { path: 'src/index.ts', size_bytes: 24 },
      { path: 'notes.txt', size_bytes: 8 },
    ]);

    expect(tree.map((node) => node.name)).toEqual(['notes.txt', 'README.md', 'src']);
    const srcNode = tree.find((node) => node.name === 'src');
    expect(srcNode?.kind).toBe('directory');
    expect(srcNode?.children?.map((node) => node.name)).toEqual(['index.ts', 'lib']);
    const libNode = srcNode?.children?.find((node) => node.name === 'lib');
    expect(libNode?.children?.[0]?.path).toBe('src/lib/util.ts');
  });

  it('builds collapsed and expanded directory state maps', () => {
    const tree = buildWorkspaceFileTree([
      { path: 'src/index.ts', size_bytes: 1 },
      { path: 'src/lib/util.ts', size_bytes: 1 },
    ]);
    const paths = collectDirectoryPaths(tree);

    expect(paths).toEqual(['src', 'src/lib']);
    expect(buildExpandedDirectoryState(tree)).toEqual({
      src: true,
      'src/lib': true,
    });
    expect(buildCollapsedDirectoryState(tree)).toEqual({
      src: false,
      'src/lib': false,
    });
  });
});
