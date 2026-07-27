<script setup lang="ts">
import type { ConversationMessageWindow } from '../../lib/conversation-message-window';
import type { OperatorThreadEntry } from '../../lib/operator-thread';

defineProps<{
  window: ConversationMessageWindow<OperatorThreadEntry>;
}>();

defineEmits<{
  earlier: [];
  newer: [];
  latest: [];
}>();
</script>

<template>
  <div class="conversation-seam__message-actions" aria-label="Conversation history pages">
    <button
      v-if="window.olderCount > 0"
      type="button"
      class="conversation-seam__meta-button"
      @click="$emit('earlier')"
    >
      Earlier ({{ window.olderCount }})
    </button>
    <button
      v-if="window.newerCount > 0"
      type="button"
      class="conversation-seam__meta-button"
      @click="$emit('newer')"
    >
      Newer
    </button>
    <button
      v-if="window.newerCount > 0"
      type="button"
      class="conversation-seam__meta-button"
      @click="$emit('latest')"
    >
      Latest
    </button>
  </div>
</template>
