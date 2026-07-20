export interface ComposerClipboardImage {
  id: string;
  name: string;
  previewUrl: string;
  mimeType: string;
  file: File;
}

export type StoredComposerAttachment = {
  id: string;
  name: string;
  mimeType: string;
  dataUrl: string;
};

/** File picker accept list for composer attachments (images + common documents).
 * Document extensions are listed first so Linux/GTK dialogs don't default to "Image Files".
 */
export const COMPOSER_ATTACHMENT_ACCEPT =
  '.pdf,.csv,.tsv,.txt,.md,.markdown,.json,application/pdf,text/csv,text/tab-separated-values,text/plain,text/markdown,application/json,image/*';

const EXTENSION_MIME_TYPES: Record<string, string> = {
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  webp: 'image/webp',
  gif: 'image/gif',
  bmp: 'image/bmp',
  avif: 'image/avif',
  heic: 'image/heic',
  heif: 'image/heif',
  pdf: 'application/pdf',
  csv: 'text/csv',
  tsv: 'text/tab-separated-values',
  txt: 'text/plain',
  md: 'text/markdown',
  markdown: 'text/markdown',
  json: 'application/json',
};

const ALLOWED_DOCUMENT_MIME_TYPES = new Set([
  'application/pdf',
  'application/csv',
  'application/json',
  'application/vnd.ms-excel',
  'text/csv',
  'text/tab-separated-values',
  'text/plain',
  'text/markdown',
]);

function mimeTypeFromFilename(name: string): string {
  const ext = name.trim().toLowerCase().split('.').pop();
  return EXTENSION_MIME_TYPES[ext ?? ''] ?? '';
}

function resolveComposerAttachmentMime(file: File): string {
  const fromFile = file.type.trim().toLowerCase();
  if (fromFile && fromFile !== 'application/octet-stream') {
    return fromFile;
  }
  return mimeTypeFromFilename(file.name) || fromFile;
}

export function isComposerImageMime(mimeType: string): boolean {
  return mimeType.trim().toLowerCase().startsWith('image/');
}

/** Tooltip for a composer attachment preview/open button. */
export function composerAttachmentPreviewTitle(name: string, mimeType: string): string {
  return isComposerImageMime(mimeType) ? `Preview ${name}` : `Open ${name}`;
}

function fileLooksLikeComposerAttachment(file: File): boolean {
  const mimeType = resolveComposerAttachmentMime(file);
  if (isComposerImageMime(mimeType)) {
    return true;
  }
  return ALLOWED_DOCUMENT_MIME_TYPES.has(mimeType);
}

function buildComposerClipboardImage(file: File, index: number): ComposerClipboardImage {
  const mimeType = resolveComposerAttachmentMime(file);
  return {
    id: `composer-attachment-${Date.now()}-${index}`,
    name: file.name?.trim() || (isComposerImageMime(mimeType) ? 'attached-image' : 'attached-file'),
    previewUrl: URL.createObjectURL(file),
    mimeType,
    file,
  };
}

export function composerAttachmentExtensionLabel(name: string, mimeType: string): string {
  const fromName = name.trim().toLowerCase().split('.').pop()?.trim();
  if (fromName && fromName !== name.trim().toLowerCase() && fromName.length <= 8) {
    return fromName.toUpperCase();
  }
  if (isComposerImageMime(mimeType)) {
    return 'IMG';
  }
  if (mimeType.includes('pdf')) {
    return 'PDF';
  }
  if (mimeType.includes('csv') || mimeType.includes('excel')) {
    return 'CSV';
  }
  if (mimeType.includes('tab-separated')) {
    return 'TSV';
  }
  if (mimeType.includes('json')) {
    return 'JSON';
  }
  if (mimeType.includes('markdown')) {
    return 'MD';
  }
  if (mimeType.startsWith('text/')) {
    return 'TXT';
  }
  return 'FILE';
}

export function readComposerImageFiles(files: FileList | File[] | null | undefined): ComposerClipboardImage[] {
  if (!files?.length) {
    return [];
  }

  const images: ComposerClipboardImage[] = [];
  for (let index = 0; index < files.length; index += 1) {
    const file = files[index];
    if (!file || !fileLooksLikeComposerAttachment(file)) {
      continue;
    }
    images.push(buildComposerClipboardImage(file, index));
  }
  return images;
}

export function readClipboardImages(event: ClipboardEvent): ComposerClipboardImage[] {
  const items = event.clipboardData?.items;
  if (!items?.length) {
    return readComposerImageFiles(event.clipboardData?.files ?? null);
  }

  const images: ComposerClipboardImage[] = [];
  for (let index = 0; index < items.length; index += 1) {
    const item = items[index];
    if (!item || item.kind !== 'file') {
      continue;
    }

    const file = item.getAsFile();
    if (!file || !fileLooksLikeComposerAttachment(file)) {
      continue;
    }

    images.push(buildComposerClipboardImage(file, index));
  }

  if (images.length) {
    return images;
  }

  return readComposerImageFiles(event.clipboardData?.files ?? null);
}

export function readDroppedImages(event: DragEvent): ComposerClipboardImage[] {
  return readComposerImageFiles(event.dataTransfer?.files ?? null);
}

export function shouldAcceptComposerFileDrop(event: DragEvent): boolean {
  const types = [...(event.dataTransfer?.types ?? [])];
  return types.includes('Files');
}

export function shouldInterceptComposerImagePaste(images: ComposerClipboardImage[]): boolean {
  return images.length > 0;
}

function dataUrlToBlob(dataUrl: string): Blob {
  const [header, payload = ''] = dataUrl.split(',');
  const mimeMatch = header.match(/^data:([^;]+)/);
  const mimeType = mimeMatch?.[1]?.trim() || 'application/octet-stream';
  const isBase64 = /;base64$/i.test(header);
  if (isBase64) {
    const binary = atob(payload);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }
    return new Blob([bytes], { type: mimeType });
  }
  return new Blob([decodeURIComponent(payload)], { type: mimeType });
}

export function composerImageFromStored(stored: StoredComposerAttachment): ComposerClipboardImage {
  const blob = dataUrlToBlob(stored.dataUrl);
  const file = new File([blob], stored.name, { type: stored.mimeType });
  return {
    id: stored.id,
    name: stored.name,
    mimeType: stored.mimeType,
    previewUrl: stored.dataUrl,
    file,
  };
}

export async function storedComposerImageFromClipboard(
  image: ComposerClipboardImage,
): Promise<StoredComposerAttachment> {
  const dataUrl = await readFileAsDataUrl(image.file);
  return {
    id: image.id,
    name: image.name,
    mimeType: image.mimeType,
    dataUrl,
  };
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        resolve(reader.result);
        return;
      }
      reject(new Error('Unable to read attachment'));
    };
    reader.onerror = () => reject(reader.error ?? new Error('Unable to read attachment'));
    reader.readAsDataURL(file);
  });
}

export function revokeComposerClipboardImages(images: ComposerClipboardImage[]): void {
  for (const image of images) {
    revokeComposerClipboardImagePreview(image);
  }
}

export function revokeComposerClipboardImagePreview(image: ComposerClipboardImage): void {
  if (image.previewUrl.startsWith('blob:')) {
    URL.revokeObjectURL(image.previewUrl);
  }
}
