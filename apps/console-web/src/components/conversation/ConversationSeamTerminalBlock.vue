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
  continueInBackground: [command: string];
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
      <button
        v-if="showTerminalBackgroundControl(messageId, segment.open)"
        type="button"
        class="agent-block__terminal-background"
        title="Mirror live shell output into vaxon (Cursor CLI still owns the process — true detach is unavailable)"
        aria-label="Background shell into vaxon terminal"
        @click="emit('background', segment)"
      >
        Background
      </button>
      <button
        v-if="!segment.open && segment.command.trim()"
        type="button"
        class="agent-block__terminal-background"
        title="Continue this command in the vaxon agent terminal so you can watch it while the agent keeps working"
        aria-label="Continue command in background agent terminal"
        @click="emit('continueInBackground', segment.command)"
      >
        Continue in background
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
