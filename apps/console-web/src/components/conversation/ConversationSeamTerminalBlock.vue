<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import type { AgentTranscriptSegment } from '../../lib/agent-transcript-blocks';
import {
  buildAgentTerminalJobView,
  shortenTerminalCommandLabel,
} from '../../lib/agent-terminal-job-view';
import { shouldShowConversationTerminalOutput } from '../../lib/conversation-terminal-display';

type TerminalSegment = Extract<AgentTranscriptSegment, { kind: 'terminal' }>;

const props = defineProps<{
  segment: TerminalSegment;
  messageId: string;
  streaming: boolean;
  /** Older shells in a huge Lead thread — header only, no job-view / output mount. */
  compact?: boolean;
  terminalMirrorBadge: (open: boolean) => string | null;
  showTerminalBackgroundControl: (messageId: string, open: boolean) => boolean;
}>();

const emit = defineEmits<{
  reveal: [segment: TerminalSegment];
  background: [segment: TerminalSegment];
  copyOutput: [output: string];
}>();

const expandedInChat = ref(false);
const showRawOutput = ref(false);

const jobView = computed(() => {
  if (props.compact) {
    const commandLabel = shortenTerminalCommandLabel(props.segment.command) || props.segment.command;
    return {
      kind: 'shell' as const,
      jobId: null,
      status: null,
      commandLabel,
      headline: null,
      displayOutput: '',
      summaryRows: [] as Array<{ label: string; value: string }>,
      isOta: /\bota(?::|\/|\b)/i.test(props.segment.command),
      isStatusPoll: false,
    };
  }
  return buildAgentTerminalJobView({
    command: props.segment.command,
    output: props.segment.output || '',
  });
});

const commandLabel = computed(
  () => jobView.value.commandLabel || props.segment.command,
);

const mirrorBadge = computed(() => props.terminalMirrorBadge(props.segment.open));
const isMirrored = computed(() => Boolean(mirrorBadge.value));
const isJobCard = computed(() => jobView.value.kind !== 'shell');

watch(isMirrored, (mirrored) => {
  // When mirror arms on a finished card, collapse chat body so the dock owns scrollback.
  // Open+streaming cards keep chat output via shouldShowConversationTerminalOutput.
  if (mirrored && !(props.segment.open && props.streaming)) {
    expandedInChat.value = false;
  }
});

const showFullOutput = computed(() =>
  shouldShowConversationTerminalOutput({
    hasOutput: Boolean(props.segment.output),
    open: props.segment.open,
    streaming: props.streaming,
    mirrored: isMirrored.value,
    expandedInChat: expandedInChat.value,
  }),
);

const statusHint = computed(() => {
  if (props.segment.open && props.streaming && isMirrored.value) {
    return jobView.value.isOta
      ? 'OTA live output streams here and in the vaxon terminal below.'
      : 'Live output streams here and in the vaxon terminal below.';
  }
  if (isMirrored.value && !expandedInChat.value) {
    return jobView.value.isOta
      ? 'Full OTA log is in the vaxon terminal below.'
      : 'Full output is in the vaxon terminal below.';
  }
  return null;
});

const bodyText = computed(() => {
  if (showRawOutput.value) {
    return props.segment.output || '';
  }
  return jobView.value.displayOutput;
});
</script>

<template>
  <div
    class="agent-block agent-block--terminal"
    :class="{
      'agent-block--terminal-mirrored': isMirrored && !expandedInChat,
      'agent-block--terminal-job': isJobCard,
      'agent-block--terminal-ota': jobView.isOta,
      'agent-block--terminal-compact': compact,
    }"
  >
    <div class="agent-block__terminal-header">
      <button
        type="button"
        class="agent-block__terminal-reveal"
        :title="
          segment.open
            ? 'Focus live shell output in the vaxon terminal'
            : 'Show this shell output in the vaxon terminal'
        "
        @click="emit('reveal', segment)"
      >
        <span class="agent-block__terminal-prompt" aria-hidden="true">$</span>
        <code class="agent-block__terminal-command">{{ commandLabel }}</code>
        <span
          v-if="jobView.headline"
          class="agent-block__terminal-jobchip"
          :data-status="jobView.status || undefined"
        >{{ jobView.headline }}</span>
        <span
          v-else-if="segment.open && streaming"
          class="agent-block__terminal-running"
        >running…</span>
        <span
          v-if="mirrorBadge"
          class="agent-block__terminal-mirrored"
        >{{ mirrorBadge }}</span>
      </button>
      <!--
        Cursor parity: Watch in terminal only while the shell tool is in flight.
        True process detach is not available from Cursor CLI yet — this reveals
        the live transcript in the dock without duplicating scrollback in chat.
      -->
      <button
        v-if="!compact && showTerminalBackgroundControl(messageId, segment.open)"
        type="button"
        class="agent-block__terminal-background"
        title="Watch this Cursor-owned shell in the vaxon terminal (chat stays as a receipt)"
        aria-label="Watch shell in vaxon terminal"
        @click="emit('background', segment)"
      >
        Watch in terminal
      </button>
      <button
        v-if="!compact && isMirrored && segment.output"
        type="button"
        class="agent-block__terminal-expand"
        :title="expandedInChat ? 'Hide chat scrollback' : 'Expand output in chat'"
        @click="expandedInChat = !expandedInChat"
      >
        {{ expandedInChat ? 'Collapse' : 'Expand in chat' }}
      </button>
      <button
        v-if="!compact && isJobCard && segment.output"
        type="button"
        class="agent-block__terminal-expand"
        :title="showRawOutput ? 'Show compact job view' : 'Show raw shell output'"
        @click="showRawOutput = !showRawOutput"
      >
        {{ showRawOutput ? 'Compact' : 'Raw' }}
      </button>
      <button
        v-if="!compact && segment.output"
        type="button"
        class="agent-block__terminal-copy"
        title="Copy terminal output"
        @click="emit('copyOutput', showRawOutput ? segment.output : bodyText)"
      >
        Copy
      </button>
    </div>
    <p
      v-if="compact"
      class="agent-block__terminal-hint"
    >Older shell receipt — expand a newer card or open the vaxon terminal for full OTA logs.</p>
    <p
      v-else-if="statusHint"
      class="agent-block__terminal-hint"
    >{{ statusHint }}</p>
    <dl
      v-if="!compact && showFullOutput && jobView.kind === 'job_status' && !showRawOutput && jobView.summaryRows.length"
      class="agent-block__terminal-summary"
    >
      <div
        v-for="row in jobView.summaryRows"
        :key="row.label"
        class="agent-block__terminal-summary-row"
      >
        <dt>{{ row.label }}</dt>
        <dd>{{ row.value }}</dd>
      </div>
    </dl>
    <pre
      v-else-if="!compact && showFullOutput"
      class="agent-block__terminal-output"
      :class="{
        'agent-block__terminal-output--job': isJobCard,
        'agent-block__terminal-output--ota': jobView.isOta,
      }"
    >{{ bodyText }}</pre>
  </div>
</template>
