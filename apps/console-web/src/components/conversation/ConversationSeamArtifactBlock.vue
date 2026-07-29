<script setup lang="ts">
import type { ChatUiAction } from '../../lib/chat-ui-action';
import { formatThreadTimestamp } from '../../lib/thread-message-view';

type ArtifactSource = { label: string; detail: string };
type ArtifactAction = {
  label: string;
  uiAction: ChatUiAction | null;
};
type ArtifactItem = {
  artifactId: string;
  title: string;
  summary: string;
  body: string;
  sources: ArtifactSource[];
  actions: ArtifactAction[];
};

defineProps<{
  artifact: ArtifactItem;
  createdAt: string;
  handoffMutationError?: string | null;
}>();

const emit = defineEmits<{
  action: [action: ArtifactAction];
}>();
</script>

<template>
  <div class="conversation-seam__meta">
    <div class="conversation-seam__meta-leading">
      <span class="conversation-seam__role">ARTIFACT</span>
      <span class="conversation-seam__command-label">{{ artifact.title }}</span>
    </div>
    <time class="conversation-seam__time" :datetime="createdAt">
      {{ formatThreadTimestamp(createdAt) }}
    </time>
  </div>
  <p class="conversation-seam__content conversation-seam__content--artifact-summary">
    {{ artifact.summary }}
  </p>
  <pre class="conversation-seam__content conversation-seam__content--artifact-body">{{
    artifact.body
  }}</pre>
  <ul v-if="artifact.sources.length" class="conversation-seam__artifact-sources">
    <li
      v-for="source in artifact.sources"
      :key="`${artifact.artifactId}:${source.label}`"
    >
      <strong>{{ source.label }}</strong>
      <span>{{ source.detail }}</span>
    </li>
  </ul>
  <div v-if="artifact.actions.length" class="conversation-seam__message-actions">
    <button
      v-for="action in artifact.actions"
      :key="`${artifact.artifactId}:${action.label}`"
      type="button"
      class="conversation-seam__meta-button"
      :class="{
        'conversation-seam__meta-button--handoff': action.uiAction?.type === 'handoff_ide',
      }"
      @click="emit('action', action)"
    >
      {{ action.label }}
    </button>
  </div>
  <p
    v-if="handoffMutationError"
    class="conversation-seam__handoff-error"
    role="alert"
  >
    {{ handoffMutationError }}
  </p>
</template>
