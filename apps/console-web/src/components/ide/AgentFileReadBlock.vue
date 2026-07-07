<script setup lang="ts">
import { computed } from 'vue';

import {
  deriveAgentReportTitle,
  extractReadMarkdownFilePath,
  splitAgentMessageForPreview,
} from '../../lib/agent-message-markdown';
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  content: string;
}>();

const shell = useShellStore();
const parts = computed(() => splitAgentMessageForPreview(props.content));
const filePath = computed(() => extractReadMarkdownFilePath(props.content));
const linkLabel = computed(
  () => filePath.value ?? deriveAgentReportTitle(parts.value.markdownSource),
);

function openFile(): void {
  const path = filePath.value;
  if (path) {
    void shell.openWorkspaceFile(path);
    return;
  }
  shell.openAgentContentInEditor({
    title: deriveAgentReportTitle(parts.value.markdownSource),
    content: parts.value.markdownSource,
    preferPreview: false,
  });
}
</script>

<template>
  <button
    type="button"
    class="agent-block agent-block--file-read"
    :title="`Open ${linkLabel} in editor`"
    @click="openFile"
  >
    <span class="agent-block__file-read-path">{{ linkLabel }}</span>
  </button>
  <p v-if="parts.postamble" class="conversation-seam__postamble">
    {{ parts.postamble }}
  </p>
</template>
