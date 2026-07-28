import { ref } from 'vue';

import { uploadChatAttachment } from '../../api/chat-api';
import {
  type ComposerClipboardImage,
  COMPOSER_ATTACHMENT_ACCEPT,
  readClipboardImages,
  readComposerImageFiles,
  readDroppedImages,
  revokeComposerClipboardImages,
  revokeComposerClipboardImagePreview,
  shouldAcceptComposerFileDrop,
  shouldInterceptComposerImagePaste,
} from '../../lib/composer-clipboard-paste';

const pendingAttachments = ref<ComposerClipboardImage[]>([]);
const attachError = ref<string | null>(null);

export function useVaxonConversationAttachments() {
  function clearAttachments(): void {
    revokeComposerClipboardImages(pendingAttachments.value);
    pendingAttachments.value = [];
    attachError.value = null;
  }

  function addFiles(files: ComposerClipboardImage[]): void {
    if (!files.length) {
      return;
    }
    pendingAttachments.value = [...pendingAttachments.value, ...files];
    attachError.value = null;
  }

  function removeAttachment(id: string): void {
    const next: ComposerClipboardImage[] = [];
    for (const item of pendingAttachments.value) {
      if (item.id === id) {
        revokeComposerClipboardImagePreview(item);
        continue;
      }
      next.push(item);
    }
    pendingAttachments.value = next;
  }

  async function pickFiles(): Promise<void> {
    if (typeof document === 'undefined') {
      return;
    }
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = COMPOSER_ATTACHMENT_ACCEPT;
    input.multiple = true;
    input.onchange = () => {
      const list = input.files;
      if (!list?.length) {
        return;
      }
      addFiles(readComposerImageFiles(Array.from(list)));
    };
    input.click();
  }

  function handlePaste(event: ClipboardEvent): boolean {
    if (!shouldInterceptComposerImagePaste(event)) {
      return false;
    }
    const images = readClipboardImages(event);
    if (!images.length) {
      return false;
    }
    event.preventDefault();
    addFiles(images);
    return true;
  }

  function handleDrop(event: DragEvent): boolean {
    if (!shouldAcceptComposerFileDrop(event)) {
      return false;
    }
    event.preventDefault();
    addFiles(readDroppedImages(event));
    return true;
  }

  async function uploadPending(workspaceId: string): Promise<string[]> {
    const files = pendingAttachments.value.map((item) => item.file);
    if (!files.length) {
      return [];
    }
    const ids: string[] = [];
    for (const file of files) {
      const record = await uploadChatAttachment(workspaceId, file);
      const id = String(record.attachment_id || '').trim();
      if (id) {
        ids.push(id);
      }
    }
    return ids;
  }

  return {
    pendingAttachments,
    attachError,
    clearAttachments,
    addFiles,
    removeAttachment,
    pickFiles,
    handlePaste,
    handleDrop,
    uploadPending,
    accept: COMPOSER_ATTACHMENT_ACCEPT,
  };
}
