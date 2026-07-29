<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import type { AgentTranscriptSegment } from '../../lib/agent-transcript-blocks';

type TerminalSegment = Extract<AgentTranscriptSegment, { kind: 'terminal' }>;

const props = defineProps<{
  segment: TerminalSegment;
  messageId: string;
  streaming: boolean;
  terminalMirrorBadge: (open: boolean) => string | null;
  showTerminalBackgroundControl: (messageId: string, open: boolean) => boolean;
}>();

const emit = defineEmits<{
  reveal: [segment: TerminalSegment];
  background: [segment: TerminalSegment];
  copyOutput: [output: string];
}>();

const expandedInChat = ref(false);

const mirrorBadge = computed(() => props.terminalMirrorBadge(props.segment.open));
const isMirrored = computed(() => Boolean(mirrorBadge.value));

watch(isMirrored, (mirrored) => {
  // When mirror arms, collapse chat body so the dock owns the scrollback.
  if (mirrored) {
    expandedInChat.value = false;
  }
});

const showFullOutput = computed(() => {
  if (!props.segment.output) {
    return false;
  }
  // Cursor-like: when watching in the terminal dock, chat keeps a receipt only.
  if (isMirrored.value && !expandedInChat.value) {
    return false;
  }
  return true;
});

const statusHint = computed(() => {
  if (isMirrored.value && !expandedInChat.value) {
    return props.segment.open && props.streaming
      ? 'Live output is in the vaxon terminal below — agent stream stays here as a receipt.'
      : 'Full output is in the vaxon terminal below.';
  }
  return null;
});
</script>

<template>
  <div
    class="agent-block agent-block--terminal"
    :class="{ 'agent-block--terminal-mirrored': isMirrored && !expandedInChat }"
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
        <code class="agent-block__terminal-command">{{ segment.command }}</code>
        <span
          v-if="segment.open && streaming"
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
        v-if="showTerminalBackgroundControl(messageId, segment.open)"
        type="button"
        class="agent-block__terminal-background"
        title="Watch this Cursor-owned shell in the vaxon terminal (chat stays as a receipt)"
        aria-label="Watch shell in vaxon terminal"
        @click="emit('background', segment)"
      >
        Watch in terminal
      </button>
      <button
        v-if="isMirrored && segment.output"
        type="button"
        class="agent-block__terminal-expand"
        :title="expandedInChat ? 'Hide chat scrollback' : 'Expand output in chat'"
        @click="expandedInChat = !expandedInChat"
      >
        {{ expandedInChat ? 'Collapse' : 'Expand in chat' }}
      </button>
      <button
        v-if="segment.output"
        type="button"
        class="agent-block__terminal-copy"
        title="Copy terminal output"
        @click="emit('copyOutput', segment.output)"
      >
        Copy
      </button>
    </div>
    <p
      v-if="statusHint"
      class="agent-block__terminal-hint"
    >{{ statusHint }}</p>
    <pre
      v-if="showFullOutput"
      class="agent-block__terminal-output"
    >{{ segment.output }}</pre>
  </div>
</template>
