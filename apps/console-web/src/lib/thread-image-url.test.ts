import { describe, expect, it } from 'vitest';

import {
  normalizeGeneratedImagePath,
  rewriteMarkdownImageSources,
  resolveEditorImagePreviewUrl,
  resolveThreadImageUrl,
  threadAttachmentUrlForImagePath,
} from './thread-image-url';

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

  it('relativizes absolute assets paths for canvas preview urls', () => {
    expect(
      resolveThreadImageUrl(
        '/home/edp/cursor/projects/home-edp-Projectx-client-young-ea/assets/evidence-storytelling-mildred.png',
        {
          workspaceId: 'workspace_young_eagles_day_care',
          projectRoot: '/home/edp/cursor/projects/home-edp-Projectx-client-young-ea',
        },
      ),
    ).toBe(
      '/api/workspaces/workspace_young_eagles_day_care/files/assets/evidence-storytelling-mildred.png/raw',
    );
  });

  it('collapses foreign absolute image paths onto assets/<basename>', () => {
    expect(
      normalizeGeneratedImagePath(
        '/tmp/elsewhere/evidence-block-play-mildred.png',
        '/home/edp/cursor/projects/home-edp-Projectx-client-young-ea',
      ),
    ).toBe('assets/evidence-block-play-mildred.png');
  });

  it('prefers persisted attachment urls when provided', () => {
    expect(
      resolveThreadImageUrl('axon-x-mobile-glass-3d-mockup.png', {
        workspaceId: 'workspace_axon_watch',
        attachmentUrl: '/api/chat/attachments/attachment_123',
      }),
    ).toBe('/api/chat/attachments/attachment_123');
  });

  it('uses draft canvas previewUrl for editor image preview', () => {
    expect(
      resolveEditorImagePreviewUrl({
        isImageDocument: true,
        source: 'draft',
        previewUrl: '/api/chat/attachments/attachment_abc',
        filePath: 'assets/evidence-block-play-mildred.png',
        title: 'evidence-block-play-mildred.png',
      }),
    ).toBe('/api/chat/attachments/attachment_abc');
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
