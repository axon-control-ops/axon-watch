<script setup lang="ts">
import { clearBriefingSurfaceOffer } from './conversation-briefing-surface';
import { kairoConversationReply } from './kairo-conversation-state';
import { useBriefingSurfacePrompt } from './use-briefing-surface-prompt';
import { useShellStore } from '../../stores/shell';

const props = withDefaults(
  defineProps<{
    compact?: boolean;
  }>(),
  {
    compact: false,
  },
);

const shell = useShellStore();
const { active, remainingSeconds, hint } = useBriefingSurfacePrompt();

function openBriefing(): void {
  clearBriefingSurfaceOffer();
  kairoConversationReply.value = '';
  shell.focusKairoBriefing();
}
</script>

<template>
  <div
    v-if="active"
    class="briefing-surface-followup"
    :class="{ 'briefing-surface-followup--compact': props.compact }"
    role="status"
    aria-live="polite"
  >
    <p class="briefing-surface-followup__copy">
      {{ hint }}
      <span class="briefing-surface-followup__timer">{{ remainingSeconds }}s</span>
    </p>
    <button type="button" class="briefing-surface-followup__action" @click.stop="openBriefing">
      Show written briefing
    </button>
  </div>
</template>
