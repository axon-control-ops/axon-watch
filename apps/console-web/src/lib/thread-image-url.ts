import { resolveChatAttachmentUrl } from '../api/chat-api';
import { resolveWorkspaceFileRawUrl } from '../api/workspace-api';

export interface ThreadImageDisplayOptions {
  workspaceId?: string | null;
  attachmentUrl?: string | null;
}

const IMAGE_EXTENSIONS = new Set(['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg', 'avif']);

/** Bare generated-image filenames are stored under assets/ in this workspace. */
export function normalizeGeneratedImagePath(path: string): string {
  const cleaned = String(path ?? '').trim().replace(/^\/+/, '');
  if (!cleaned || cleaned.includes('/')) {
    return cleaned;
  }
  return `assets/${cleaned}`;
}

function isImagePath(value: string): boolean {
  const cleaned = value.trim();
  if (!cleaned || /^https?:\/\//i.test(cleaned) || cleaned.startsWith('data:')) {
    return false;
  }
  const extension = cleaned.split('.').pop()?.toLowerCase() ?? '';
  return IMAGE_EXTENSIONS.has(extension);
}

export function resolveThreadImageUrl(
  source: string,
  options: ThreadImageDisplayOptions = {},
): string {
  const attachmentUrl = String(options.attachmentUrl ?? '').trim();
  if (attachmentUrl) {
    return resolveChatAttachmentUrl(attachmentUrl);
  }

  const normalized = String(source ?? '').trim();
  if (!normalized) {
    return '';
  }
  if (/^https?:\/\//i.test(normalized) || normalized.startsWith('data:')) {
    return normalized;
  }
  if (normalized.startsWith('/api/chat/attachments/')) {
    return resolveChatAttachmentUrl(normalized);
  }
  const workspaceId = options.workspaceId?.trim();
  if (workspaceId && isImagePath(normalized)) {
    const path = normalizeGeneratedImagePath(normalized);
    return resolveWorkspaceFileRawUrl(workspaceId, path);
  }
  return normalized;
}

export function threadAttachmentUrlForImagePath(
  path: string,
  attachments: ReadonlyArray<{ filename: string; url: string }> = [],
): string | null {
  const normalized = normalizeGeneratedImagePath(String(path ?? '').trim());
  const fileName = normalized.split('/').pop() ?? normalized;
  if (!fileName) {
    return null;
  }
  const match = attachments.find((attachment) => {
    const attachmentName = String(attachment.filename ?? '').trim();
    return attachmentName === fileName || attachmentName === normalized;
  });
  const url = String(match?.url ?? '').trim();
  return url || null;
}

export function rewriteMarkdownImageSources(
  html: string,
  options: { workspaceId?: string | null } = {},
): string {
  if (!html.includes('<img')) {
    return html;
  }
  return html.replace(
    /<img\b([^>]*?)\bsrc="([^"]+)"([^>]*)>/gi,
    (_match, before: string, src: string, after: string) => {
      const resolved = resolveThreadImageUrl(src, options);
      return `<img${before}src="${resolved}"${after}>`;
    },
  );
}
