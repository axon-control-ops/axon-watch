import { describe, expect, it } from 'vitest';

import { rewriteMarkdownImageSources, resolveThreadImageUrl, threadAttachmentUrlForImagePath } from './thread-image-url';

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

  it('prefers persisted attachment urls when provided', () => {
    expect(
      resolveThreadImageUrl('axon-x-mobile-glass-3d-mockup.png', {
        workspaceId: 'workspace_axon_watch',
        attachmentUrl: '/api/chat/attachments/attachment_123',
      }),
    ).toBe('/api/chat/attachments/attachment_123');
  });

  it('matches attachment urls by image filename', () => {
    expect(
      threadAttachmentUrlForImagePath('axon-x-mobile-glass-3d-mockup.png', [
        {
          filename: 'axon-x-mobile-glass-3d-mockup.png',
          url: '/api/chat/attachments/attachment_123',
        },
      ]),
    ).toBe('/api/chat/attachments/attachment_123');
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
