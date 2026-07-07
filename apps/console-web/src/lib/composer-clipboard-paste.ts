export interface ComposerClipboardImage {
  id: string;
  name: string;
  previewUrl: string;
  mimeType: string;
  file: File;
}

function imageTypeFromFilename(name: string): string {
  const ext = name.trim().toLowerCase().split('.').pop();
  const types: Record<string, string> = {
    png: 'image/png',
    jpg: 'image/jpeg',
    jpeg: 'image/jpeg',
    webp: 'image/webp',
    gif: 'image/gif',
    bmp: 'image/bmp',
    avif: 'image/avif',
    heic: 'image/heic',
    heif: 'image/heif',
  };
  return types[ext ?? ''] ?? '';
}

function fileLooksLikeComposerImage(file: File): boolean {
  const mimeType = file.type.trim() || imageTypeFromFilename(file.name);
  return mimeType.startsWith('image/');
}

function buildComposerClipboardImage(file: File, index: number): ComposerClipboardImage {
  const mimeType = file.type.trim() || imageTypeFromFilename(file.name);
  return {
    id: `composer-image-${Date.now()}-${index}`,
    name: file.name?.trim() || 'attached-image',
    previewUrl: URL.createObjectURL(file),
    mimeType,
    file,
  };
}

export function readComposerImageFiles(files: FileList | File[] | null | undefined): ComposerClipboardImage[] {
  if (!files?.length) {
    return [];
  }

  const images: ComposerClipboardImage[] = [];
  for (let index = 0; index < files.length; index += 1) {
    const file = files[index];
    if (!file || !fileLooksLikeComposerImage(file)) {
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
    if (!file || !fileLooksLikeComposerImage(file)) {
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

export function revokeComposerClipboardImages(images: ComposerClipboardImage[]): void {
  for (const image of images) {
    URL.revokeObjectURL(image.previewUrl);
  }
}
