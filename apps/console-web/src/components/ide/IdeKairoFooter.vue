<script setup lang="ts">
import { computed } from 'vue';

import KairoChip from '../KairoChip.vue';
import {
  briefingAdvise,
  briefingNotice,
  briefingPanelHeadline,
} from '../../lib/briefing-panel-view';
import { kairoPresenceLabel } from '../../lib/kairo-presence';
import { ideShowKairoSidebarExpanded } from '../../lib/ide-presence-profile';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const showExpandedPanel = computed(() =>
  ideShowKairoSidebarExpanded(shell.idePresenceProfile),
);

const headline = computed(() => {
  if (shell.kairoAgentLiveLine) {
    return shell.kairoAgentLiveLine.replace(/^KAIRO —\s*/, '');
  }
  return briefingPanelHeadline(shell.operatorBriefing, shell.briefingLoadState);
});
const notice = computed(() => {
  if (shell.kairoAgentLiveLine) {
    return 'Streaming agent activity — thinking, tools, and edits appear here as they land.';
  }
  return briefingNotice(shell.operatorBriefing, shell.briefingLoadState);
});
const advise = computed(() =>
  briefingAdvise(shell.operatorBriefing, shell.briefingLoadState),
);
const approvalBadge = computed(() => shell.pendingApprovalsCount);
const signalBadge = computed(
  () => shell.operatorBriefing?.top_signals.length ?? shell.runtimeSummary?.signals.open_count ?? 0,
);
</script>

<template>
  <footer class="ide-kairo-footer" aria-label="KAIRO presence">
    <KairoChip
      v-if="!showExpandedPanel"
      class="ide-kairo-footer__chip"
      :state="shell.ideDisplayKairoPresenceState"
      @open-briefing="shell.focusKairoBriefing()"
    />
    <button
      v-else
      type="button"
      class="ide-kairo-footer__interrupt hud-panel-frame"
      :class="`ide-kairo-footer__interrupt--${shell.kairoPresenceState}`"
      :aria-label="`KAIRO. ${shell.briefingSummaryLine}`"
      @click="shell.focusKairoBriefing()"
    >
      <div class="ide-kairo-footer__interrupt-head">
        <span class="ide-kairo-footer__interrupt-title">KAIRO</span>
        <span class="ide-kairo-footer__interrupt-state">
          {{ kairoPresenceLabel(shell.kairoPresenceState) }}
        </span>
      </div>
      <p class="ide-kairo-footer__interrupt-headline">{{ headline }}</p>
      <p v-if="notice" class="ide-kairo-footer__interrupt-copy">{{ notice }}</p>
      <p v-if="advise" class="ide-kairo-footer__interrupt-copy">{{ advise }}</p>
      <div v-if="approvalBadge || signalBadge" class="ide-kairo-footer__badges">
        <span v-if="approvalBadge" class="ide-kairo-footer__badge">
          {{ approvalBadge }} approval{{ approvalBadge === 1 ? '' : 's' }}
        </span>
        <span v-if="signalBadge" class="ide-kairo-footer__badge ide-kairo-footer__badge--signal">
          {{ signalBadge }} signal{{ signalBadge === 1 ? '' : 's' }}
        </span>
      </div>
    </button>
  </footer>
</template>
