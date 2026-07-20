<script setup lang="ts">
import { resolveChatAttachmentUrl } from '../../api/control-plane';
import type { ThreadMessageAttachment } from '../../lib/operator-thread';
import {
  isThreadImageAttachment,
  threadAttachmentExtensionLabel,
  threadAttachmentPreviewTitle,
} from '../../lib/thread-message-attachment-view';

defineProps<{
  attachments: ThreadMessageAttachment[];
}>();

const emit = defineEmits<{
  preview: [attachment: ThreadMessageAttachment];
}>();

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
        'conversation-seam__attachment-card--file': !isThreadImageAttachment(attachment),
      }"
      :title="threadAttachmentPreviewTitle(attachment)"
      :aria-label="threadAttachmentPreviewTitle(attachment)"
      @click="emit('preview', attachment)"
    >
      <img
        v-if="isThreadImageAttachment(attachment)"
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
          {{ threadAttachmentExtensionLabel(attachment) }}
        </span>
        <span class="conversation-seam__attachment-file-label">{{ attachment.filename }}</span>
      </span>
    </button>
  </div>
</template>
