<script setup lang="ts">
import type { AgentQuestionOption } from '../../lib/agent-question-view';
import type { AgentTranscriptSegment } from '../../lib/agent-transcript-blocks';
import AgentPlanBlock from './AgentPlanBlock.vue';
import AgentQuestionBlock from './AgentQuestionBlock.vue';
import AgentResearchBlock from './AgentResearchBlock.vue';

defineProps<{
  segment: Extract<
    AgentTranscriptSegment,
    { kind: 'plan' } | { kind: 'question' } | { kind: 'research' }
  >;
  workspaceId: string | null;
  live?: boolean;
  messageId?: string;
  answeredOption?: AgentQuestionOption | null;
}>();
</script>

<template>
  <AgentPlanBlock
    v-if="segment.kind === 'plan'"
    :plan-id="segment.planId"
    :title="segment.title"
    :workspace-id="workspaceId"
  />
  <AgentQuestionBlock
    v-else-if="segment.kind === 'question'"
    :prompt="segment.prompt"
    :options="segment.options"
    :live="live"
    :message-id="messageId"
    :answered-option="answeredOption"
  />
  <AgentResearchBlock
    v-else
    :query="segment.query"
    :items="segment.items"
    :provider="segment.provider"
    :kind="segment.kindLabel"
    :live="live"
  />
</template>
