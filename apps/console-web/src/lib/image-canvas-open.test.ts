import { describe, expect, it } from 'vitest';

import { buildImageCanvasDocument, imageCanvasDocumentId } from './image-canvas-open';

describe('image canvas open', () => {
  it('opens attachment-backed images as draft canvas tabs', () => {
    const doc = buildImageCanvasDocument({
      path: '/home/edp/Documents/Mildred_Mathebula/13855/generated_assets/evidence-block-play-mildred.png',
      attachmentUrl: '/api/chat/attachments/attachment_abc',
      workspaceId: 'workspace_young_eagles_day_care',
      projectRoot: '/home/edp/Projectx/client/young-eagles-day-care',
    });
    expect(doc?.id).toBe(imageCanvasDocumentId('evidence-block-play-mildred.png'));
    expect(doc?.source).toBe('draft');
    expect(doc?.language).toBe('image');
    expect(doc?.previewUrl).toBe('/api/chat/attachments/attachment_abc');
    expect(doc?.filePath).toBe('assets/evidence-block-play-mildred.png');
  });

  it('returns null when only a missing workspace assets path is available', () => {
    const doc = buildImageCanvasDocument({
      path: 'assets/evidence-block-play-mildred.png',
      workspaceId: 'workspace_young_eagles_day_care',
      projectRoot: '/home/edp/Projectx/client/young-eagles-day-care',
    });
    expect(doc).toBeNull();
  });
});
