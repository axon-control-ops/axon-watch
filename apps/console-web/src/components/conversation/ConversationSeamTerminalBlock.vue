<script setup lang="ts">
import type { AgentTranscriptSegment } from '../../lib/agent-transcript-blocks';

type TerminalSegment = Extract<AgentTranscriptSegment, { kind: 'terminal' }>;

defineProps<{
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
</script>

<template>
  <div class="agent-block agent-block--terminal">
    <div class="agent-block__terminal-header">
      <button
        type="button"
        class="agent-block__terminal-reveal"
        :title="
          segment.open
            ? 'Show live shell output in the vaxon terminal'
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
          v-if="terminalMirrorBadge(segment.open)"
          class="agent-block__terminal-mirrored"
        >{{ terminalMirrorBadge(segment.open) }}</span>
      </button>
      <!--
        Cursor parity: Move / Watch in background only while the shell tool is
        still in flight. Finished cards are history — no re-run CTA.
      -->
      <button
        v-if="showTerminalBackgroundControl(messageId, segment.open)"
        type="button"
        class="agent-block__terminal-background"
        title="Watch this live Cursor-owned shell in the vaxon terminal"
        aria-label="Watch shell in vaxon terminal"
        @click="emit('background', segment)"
      >
        Watch in terminal
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
    <pre
      v-if="segment.output"
      class="agent-block__terminal-output"
    >{{ segment.output }}</pre>
  </div>
</template>
