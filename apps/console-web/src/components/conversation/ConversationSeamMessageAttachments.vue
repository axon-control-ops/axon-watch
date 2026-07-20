<script setup lang="ts">
import { resolveChatAttachmentUrl } from '../../api/control-plane';
import { composerAttachmentExtensionLabel } from '../../lib/composer-clipboard-paste';
import type { ThreadMessageAttachment } from '../../lib/operator-thread';

defineProps<{
  attachments: ThreadMessageAttachment[];
}>();

const emit = defineEmits<{
  preview: [attachment: ThreadMessageAttachment];
}>();

function isImageAttachment(attachment: ThreadMessageAttachment): boolean {
  return attachment.mime_type.startsWith('image/');
}
</script>

<template>
  <div
    v-if="attachments.length"
    class="conversation-seam__attachments conversation-seam__attachments--thread"
    aria-label="Message attachments"
  >
    <button
      v-for="attachment in attachments"
      :key="attachment.attachment_id"
      type="button"
      class="conversation-seam__attachment-card conversation-seam__attachment-card--thread"
      :class="{
        'conversation-seam__attachment-card--file': !isImageAttachment(attachment),
      }"
      :title="isImageAttachment(attachment) ? `Preview ${attachment.filename}` : `Open ${attachment.filename}`"
      @click="emit('preview', attachment)"
    >
      <img
        v-if="isImageAttachment(attachment)"
        class="conversation-seam__attachment-preview"
        :src="resolveChatAttachmentUrl(attachment.url)"
        :alt="attachment.filename"
        loading="lazy"
      >
      <span
        v-else
        class="conversation-seam__attachment-file"
      >
        <span class="conversation-seam__attachment-file-ext">
          {{ composerAttachmentExtensionLabel(attachment.filename, attachment.mime_type) }}
        </span>
        <span class="conversation-seam__attachment-file-label">{{ attachment.filename }}</span>
      </span>
    </button>
  </div>
</template>
