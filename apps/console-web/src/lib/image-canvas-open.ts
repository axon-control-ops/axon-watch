import type { WorkspaceDocumentDescriptor } from './workspace-documents';
import { normalizeGeneratedImagePath, resolveThreadImageUrl } from './thread-image-url';

export function imageCanvasDocumentId(pathOrName: string): string {
  const base = pathOrName.split('/').pop()?.trim() || pathOrName.trim() || 'image';
  return `image-canvas:${base}`;
}

export function upsertImageCanvasDocument(
  drafts: WorkspaceDocumentDescriptor[],
  doc: WorkspaceDocumentDescriptor,
): WorkspaceDocumentDescriptor[] {
  if (drafts.some((row) => row.id === doc.id)) {
    return drafts.map((row) => (row.id === doc.id ? doc : row));
  }
  return [...drafts, doc];
}

/** Build or refresh a canvas tab for an agent image (attachment preferred). */
export function buildImageCanvasDocument(input: {
  path: string;
  attachmentUrl?: string | null;
  workspaceId?: string | null;
  projectRoot?: string | null;
}): WorkspaceDocumentDescriptor | null {
  const path = String(input.path ?? '').trim();
  if (!path) {
    return null;
  }
  const openPath =
    normalizeGeneratedImagePath(path, input.projectRoot) || path.split('/').pop() || path;
  const fileName = openPath.split('/').pop() || openPath;
  const attachmentUrl = String(input.attachmentUrl ?? '').trim();
  // Prefer chat attachment URLs — agent images often live outside the bound
  // project root, so workspace `assets/…` raw file fetches 404.
  const previewUrl = resolveThreadImageUrl(path, {
    workspaceId: input.workspaceId,
    projectRoot: input.projectRoot,
    attachmentUrl: attachmentUrl || null,
  });
  if (!previewUrl) {
    return null;
  }
  const attachmentBacked =
    Boolean(attachmentUrl) ||
    previewUrl.includes('/api/chat/attachments/') ||
    previewUrl.startsWith('data:');
  if (!attachmentBacked && !/^https?:\/\//i.test(previewUrl)) {
    // Workspace-relative raw URLs alone are not enough for foreign agent paths.
    return null;
  }
  return {
    id: imageCanvasDocumentId(fileName),
    title: fileName,
    language: 'image',
    value: '',
    description: 'Image canvas preview.',
    source: 'draft',
    filePath: openPath,
    readOnly: true,
    dirty: false,
    previewUrl,
  };
}
