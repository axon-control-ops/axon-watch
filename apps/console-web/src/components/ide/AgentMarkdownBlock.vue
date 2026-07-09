<script setup lang="ts">
import { computed } from 'vue';

import {
  renderAgentMessageMarkdown,
  splitAgentMessageForPreview,
} from '../../lib/agent-message-markdown';
import { handleMarkdownContainerClick } from '../../lib/markdown-link-click';
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  content: string;
}>();

const shell = useShellStore();
const parts = computed(() => splitAgentMessageForPreview(props.content));
const previewHtml = computed(() => renderAgentMessageMarkdown(props.content));

function handleMarkdownClick(event: MouseEvent): void {
  handleMarkdownContainerClick(event, {
    openWorkspaceFile: (path) => shell.openWorkspaceFile(path),
  });
}
</script>

<template>
  <p v-if="parts.preamble" class="conversation-seam__preamble">
    {{ parts.preamble }}
  </p>
  <div
    class="conversation-seam__content conversation-seam__content--markdown conversation-seam__content--agent"
    v-html="previewHtml"
    @click="handleMarkdownClick"
  />
  <p v-if="parts.postamble" class="conversation-seam__postamble">
    {{ parts.postamble }}
  </p>
</template>
