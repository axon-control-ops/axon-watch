import { describe, expect, it } from 'vitest';

import { rewriteMarkdownImageSources, resolveThreadImageUrl } from './thread-image-url';

describe('thread image urls', () => {
  it('rewrites workspace image paths to raw file urls', () => {
    expect(
      resolveThreadImageUrl('assets/mockup.png', { workspaceId: 'workspace_axon_watch' }),
    ).toBe('/api/workspaces/workspace_axon_watch/files/assets/mockup.png/raw');
  });

  it('rewrites bare generated image filenames to assets paths', () => {
    expect(
      resolveThreadImageUrl('axon-x-mobile-glass-3d-mockup.png', {
        workspaceId: 'workspace_axon_watch',
      }),
    ).toBe(
      '/api/workspaces/workspace_axon_watch/files/assets/axon-x-mobile-glass-3d-mockup.png/raw',
    );
  });

  it('rewrites markdown image tags to resolved urls', () => {
    const html = rewriteMarkdownImageSources(
      '<p>Preview</p><img src="assets/mockup.png" alt="mockup">',
      { workspaceId: 'workspace_axon_watch' },
    );

    expect(html).toContain(
      'src="/api/workspaces/workspace_axon_watch/files/assets/mockup.png/raw"',
    );
  });
});
