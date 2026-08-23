<script setup lang="ts">
import type { AgentQuestionOption } from '../../lib/agent-question-view';
import type { AgentTranscriptSegment } from '../../lib/agent-transcript-blocks';
import AgentLeadFanOutBlock from './AgentLeadFanOutBlock.vue';
import AgentLeadCheckinBlock from './AgentLeadCheckinBlock.vue';
import AgentLeadStandupBlock from './AgentLeadStandupBlock.vue';
import AgentPlanBlock from './AgentPlanBlock.vue';
import AgentQuestionBlock from './AgentQuestionBlock.vue';
import AgentResearchBlock from './AgentResearchBlock.vue';

defineProps<{
  segment: Extract<
    AgentTranscriptSegment,
    | { kind: 'plan' }
    | { kind: 'question' }
    | { kind: 'research' }
    | { kind: 'lead-fan-out' }
    | { kind: 'lead-standup' }
    | { kind: 'lead-checkin' }
  >;
  workspaceId: string | null;
  live?: boolean;
  messageId?: string;
  segmentIndex?: number;
  answeredOption?: AgentQuestionOption | null;
}>();
</script>

<template>
  <AgentLeadFanOutBlock
    v-if="segment.kind === 'lead-fan-out'"
    :plan-id="segment.planId"
    :mode="segment.mode"
    :lead-name="segment.leadName"
    :title="segment.title"
    :queued="segment.queued"
    :deferred="segment.deferred"
    :assignments="segment.assignments"
    :notes="segment.notes"
  />
  <AgentLeadStandupBlock
    v-else-if="segment.kind === 'lead-standup'"
    :lead-name="segment.leadName"
    :title="segment.title"
    :intro="segment.intro"
    :body-markdown="segment.bodyMarkdown"
    :confidence="segment.confidence"
    :verification-notice="segment.verificationNotice"
    :workspace-id="workspaceId"
  />
  <AgentLeadCheckinBlock
    v-else-if="segment.kind === 'lead-checkin'"
    :title="segment.title"
    :summary="segment.summary"
    :findings="segment.findings"
    :next-steps="segment.nextSteps"
    :prompt="segment.prompt"
    :options="segment.options"
    :message-id="messageId"
    :segment-index="segmentIndex"
    :answered-option="answeredOption"
  />
  <AgentPlanBlock
    v-else-if="segment.kind === 'plan'"
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
    :segment-index="segmentIndex"
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
