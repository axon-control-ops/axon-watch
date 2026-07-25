import { resolveChatAttachmentUrl } from '../api/chat-api';
import { resolveWorkspaceFileRawUrl } from '../api/workspace-api';

export interface ThreadImageDisplayOptions {
  workspaceId?: string | null;
  /** Bound project root — used to relativize absolute agent paths for canvas open/preview. */
  projectRoot?: string | null;
  attachmentUrl?: string | null;
}

const IMAGE_EXTENSIONS = new Set(['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg', 'avif']);

function normalizeSlashes(path: string): string {
  return path.replace(/\\/g, '/');
}

function isAbsolutePath(path: string): boolean {
  return path.startsWith('/') || /^[A-Za-z]:\//.test(path);
}

/**
 * Map agent/image paths onto workspace-relative file paths the canvas can open.
 * Absolute paths are relativized via project root, or collapsed to an `assets/…` suffix.
 */
export function normalizeGeneratedImagePath(
  path: string,
  projectRoot?: string | null,
): string {
  const raw = normalizeSlashes(String(path ?? '').trim());
  if (!raw || /^https?:\/\//i.test(raw) || raw.startsWith('data:')) {
    return '';
  }

  const root = normalizeSlashes(String(projectRoot ?? '').trim()).replace(/\/+$/, '');
  if (root && (raw === root || raw.startsWith(`${root}/`))) {
    const relative = raw === root ? '' : raw.slice(root.length + 1);
    if (!relative) {
      return '';
    }
    return relative.replace(/^\/+/, '');
  }

  const assetsMarker = '/assets/';
  const assetsIdx = raw.toLowerCase().lastIndexOf(assetsMarker);
  if (assetsIdx >= 0) {
    return raw.slice(assetsIdx + 1);
  }
  if (raw.toLowerCase().startsWith('assets/')) {
    return raw.replace(/^\/+/, '');
  }

  const cleaned = raw.replace(/^\/+/, '');
  if (!cleaned) {
    return '';
  }
  if (!cleaned.includes('/')) {
    return `assets/${cleaned}`;
  }
  // Absolute-or-foreign path without assets/ — open by basename under assets/.
  if (isAbsolutePath(raw)) {
    const base = cleaned.split('/').pop() || cleaned;
    return base.includes('.') ? `assets/${base}` : base;
  }
  return cleaned;
}

function isImagePath(value: string): boolean {
  const cleaned = value.trim();
  if (!cleaned || /^https?:\/\//i.test(cleaned) || cleaned.startsWith('data:')) {
    return false;
  }
  const extension = cleaned.split('.').pop()?.toLowerCase() ?? '';
  return IMAGE_EXTENSIONS.has(extension);
}

/** Editor canvas preview URL for an opened workspace image document. */
export function resolveEditorImagePreviewUrl(input: {
  workspaceId?: string | null;
  projectRoot?: string | null;
  filePath?: string | null;
  title?: string | null;
  previewUrl?: string | null;
  isImageDocument: boolean;
  source?: string | null;
}): string {
  if (!input.isImageDocument) {
    return '';
  }
  const direct = String(input.previewUrl ?? '').trim();
  if (direct) {
    // Draft canvas tabs stash a ready URL (usually chat-attachment-backed).
    if (/^https?:\/\//i.test(direct) || direct.startsWith('data:')) {
      return direct;
    }
    if (direct.startsWith('/api/chat/attachments/')) {
      return resolveChatAttachmentUrl(direct);
    }
    return resolveThreadImageUrl(direct, {
      workspaceId: input.workspaceId,
      projectRoot: input.projectRoot,
    });
  }
  if (input.source !== 'file' || !input.workspaceId?.trim()) {
    return '';
  }
  return resolveThreadImageUrl(input.filePath || input.title || '', {
    workspaceId: input.workspaceId,
    projectRoot: input.projectRoot,
  });
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
    const path = normalizeGeneratedImagePath(normalized, options.projectRoot);
    if (!path) {
      return '';
    }
    return resolveWorkspaceFileRawUrl(workspaceId, path);
  }
  return normalized;
}

export function threadAttachmentUrlForImagePath(
  path: string,
  attachments: ReadonlyArray<{ filename: string; url: string }> = [],
  projectRoot?: string | null,
): string | null {
  const normalized = normalizeGeneratedImagePath(String(path ?? '').trim(), projectRoot);
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
  options: { workspaceId?: string | null; projectRoot?: string | null } = {},
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
