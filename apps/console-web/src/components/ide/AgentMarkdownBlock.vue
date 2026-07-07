<script setup lang="ts">
import { computed } from 'vue';

import {
  renderAgentMessageMarkdown,
  splitAgentMessageForPreview,
} from '../../lib/agent-message-markdown';

const props = defineProps<{
  content: string;
}>();

const parts = computed(() => splitAgentMessageForPreview(props.content));
const previewHtml = computed(() => renderAgentMessageMarkdown(props.content));
</script>

<template>
  <p v-if="parts.preamble" class="conversation-seam__preamble">
    {{ parts.preamble }}
  </p>
  <div
    class="conversation-seam__content conversation-seam__content--markdown conversation-seam__content--agent"
    v-html="previewHtml"
  />
  <p v-if="parts.postamble" class="conversation-seam__postamble">
    {{ parts.postamble }}
  </p>
</template>
