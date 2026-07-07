export interface ComposerClipboardImage {
  id: string;
  name: string;
  previewUrl: string;
  mimeType: string;
  file: File;
}

export function readClipboardImages(event: ClipboardEvent): ComposerClipboardImage[] {
  const items = event.clipboardData?.items;
  if (!items?.length) {
    return [];
  }

  const images: ComposerClipboardImage[] = [];
  for (let index = 0; index < items.length; index += 1) {
    const item = items[index];
    if (!item || item.kind !== 'file' || !item.type.startsWith('image/')) {
      continue;
    }

    const file = item.getAsFile();
    if (!file) {
      continue;
    }

    images.push({
      id: `composer-image-${Date.now()}-${index}`,
      name: file.name?.trim() || 'pasted-image',
      previewUrl: URL.createObjectURL(file),
      mimeType: file.type,
      file,
    });
  }

  return images;
}

export function shouldInterceptComposerImagePaste(images: ComposerClipboardImage[]): boolean {
  return images.length > 0;
}

export function revokeComposerClipboardImages(images: ComposerClipboardImage[]): void {
  for (const image of images) {
    URL.revokeObjectURL(image.previewUrl);
  }
}
