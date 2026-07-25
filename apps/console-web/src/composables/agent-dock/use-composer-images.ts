import { ref } from 'vue';

import {
  type ComposerClipboardImage,
  COMPOSER_ATTACHMENT_ACCEPT,
  composerImageFromStored,
  isComposerImageMime,
  readClipboardImages,
  readComposerImageFiles,
  readDroppedImages,
  revokeComposerClipboardImages,
  revokeComposerClipboardImagePreview,
  shouldAcceptComposerFileDrop,
  shouldInterceptComposerImagePaste,
  storedComposerImageFromClipboard,
} from '../../lib/composer-clipboard-paste';
import {
  persistComposerAttachments,
  readStoredComposerAttachments,
} from '../../lib/ide-composer-attachment-prefs';

export function useComposerImages() {
  const composerImages = ref<ComposerClipboardImage[]>([]);
  const composerImagesWorkspaceId = ref<string | null>(null);
  const composerImagesThreadId = ref<string | null>(null);
  const composerImagesPersistTimer = ref<ReturnType<typeof setTimeout> | null>(null);
  const enlargedComposerImage = ref<ComposerClipboardImage | null>(null);
  const composerDragOver = ref(false);

  function clearComposerImages(options: { revokePreviews?: boolean } = {}): void {
    if (options.revokePreviews !== false) {
      revokeComposerClipboardImages(composerImages.value);
    }
    composerImages.value = [];
    schedulePersistComposerImages();
  }

  function schedulePersistComposerImages(): void {
    if (typeof window === 'undefined') {
      return;
    }
    if (composerImagesPersistTimer.value) {
      clearTimeout(composerImagesPersistTimer.value);
    }
    composerImagesPersistTimer.value = setTimeout(() => {
      composerImagesPersistTimer.value = null;
      void persistCurrentComposerImages();
    }, 180);
  }

  async function persistCurrentComposerImages(): Promise<void> {
    const workspaceId = composerImagesWorkspaceId.value;
    const threadId = composerImagesThreadId.value;
    if (!workspaceId || !threadId) {
      return;
    }
    if (!composerImages.value.length) {
      persistComposerAttachments(workspaceId, [], threadId);
      return;
    }

    const stored = await Promise.all(
      composerImages.value.map((image) => storedComposerImageFromClipboard(image)),
    );
    persistComposerAttachments(workspaceId, stored, threadId);
  }

  function loadComposerImagesForWorkspace(
    workspaceId: string | null | undefined,
    threadId?: string | null,
  ): void {
    const nextWorkspaceId = workspaceId?.trim() || null;
    const nextThreadId = threadId?.trim() || null;
    if (
      composerImagesWorkspaceId.value === nextWorkspaceId &&
      composerImagesThreadId.value === nextThreadId
    ) {
      return;
    }

    revokeComposerClipboardImages(composerImages.value);
    composerImagesWorkspaceId.value = nextWorkspaceId;
    composerImagesThreadId.value = nextThreadId;
    enlargedComposerImage.value = null;
    composerImages.value =
      nextWorkspaceId && nextThreadId
        ? readStoredComposerAttachments(nextWorkspaceId, nextThreadId).map(composerImageFromStored)
        : [];
  }

  function openComposerImage(image: ComposerClipboardImage): void {
    if (!isComposerImageMime(image.mimeType)) {
      if (typeof window !== 'undefined') {
        window.open(image.previewUrl, '_blank', 'noopener,noreferrer');
      }
      return;
    }
    enlargedComposerImage.value = image;
  }

  function closeComposerImageLightbox(): void {
    enlargedComposerImage.value = null;
  }

  function addComposerImages(images: ComposerClipboardImage[]): void {
    if (!images.length) {
      return;
    }
    composerImages.value = [...composerImages.value, ...images];
    schedulePersistComposerImages();
  }

  function openComposerAttachmentPicker(): void {
    if (typeof document === 'undefined') {
      return;
    }
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = COMPOSER_ATTACHMENT_ACCEPT;
    input.multiple = true;
    input.addEventListener('change', () => {
      addComposerImages(readComposerImageFiles(input.files));
    });
    input.click();
  }

  function handleComposerPaste(event: ClipboardEvent): void {
    const images = readClipboardImages(event);
    if (!shouldInterceptComposerImagePaste(images)) {
      return;
    }

    event.preventDefault();
    addComposerImages(images);
  }

  function handleComposerDragOver(event: DragEvent): void {
    if (!shouldAcceptComposerFileDrop(event)) {
      return;
    }
    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = 'copy';
    }
    composerDragOver.value = true;
  }

  function handleComposerDragLeave(event: DragEvent): void {
    const nextTarget = event.relatedTarget as Node | null;
    if (nextTarget && event.currentTarget instanceof Node && event.currentTarget.contains(nextTarget)) {
      return;
    }
    composerDragOver.value = false;
  }

  function handleComposerDrop(event: DragEvent): void {
    event.preventDefault();
    composerDragOver.value = false;
    const images = readDroppedImages(event);
    if (!shouldInterceptComposerImagePaste(images)) {
      return;
    }
    addComposerImages(images);
  }

  function removeComposerImage(imageId: string): void {
    const removed = composerImages.value.find((image) => image.id === imageId);
    if (removed) {
      revokeComposerClipboardImagePreview(removed);
      if (enlargedComposerImage.value?.id === imageId) {
        enlargedComposerImage.value = null;
      }
    }
    composerImages.value = composerImages.value.filter((image) => image.id !== imageId);
    schedulePersistComposerImages();
  }

  function disposeComposerImagesPersistTimer(): void {
    if (composerImagesPersistTimer.value) {
      clearTimeout(composerImagesPersistTimer.value);
      composerImagesPersistTimer.value = null;
    }
  }

  function revokeAllComposerImagePreviews(): void {
    revokeComposerClipboardImages(composerImages.value);
  }

  return {
    composerImages,
    composerImagesWorkspaceId,
    composerImagesPersistTimer,
    enlargedComposerImage,
    composerDragOver,
    clearComposerImages,
    schedulePersistComposerImages,
    persistCurrentComposerImages,
    loadComposerImagesForWorkspace,
    openComposerImage,
    closeComposerImageLightbox,
    addComposerImages,
    openComposerAttachmentPicker,
    handleComposerPaste,
    handleComposerDragOver,
    handleComposerDragLeave,
    handleComposerDrop,
    removeComposerImage,
    disposeComposerImagesPersistTimer,
    revokeAllComposerImagePreviews,
  };
}
