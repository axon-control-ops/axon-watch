<script setup lang="ts">
import { computed } from 'vue';

import {
  briefingAdvise,
  briefingNotice,
  briefingPanelHeadline,
} from '../../lib/briefing-panel-view';
import { kairoPresenceLabel } from '../../lib/kairo-presence';
import { ideShowKairoSidebarExpanded } from '../../lib/ide-presence-profile';
import { useShellStore } from '../../stores/shell';
import OperatorPersonaMark from '../OperatorPersonaMark.vue';
import AgentLiveLineHeadline from './AgentLiveLineHeadline.vue';
import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import BriefingSurfaceFollowupPrompt from '../../features/kairo-conversation/BriefingSurfaceFollowupPrompt.vue';

const shell = useShellStore();
const debugModeActive = computed(() => shell.ideDebugModeSelected);
const presenceLabel = computed(() => {
  if (!debugModeActive.value) {
    return kairoPresenceLabel(shell.kairoPresenceState);
  }
  const access = shell.agentExecutionAccess === 'full' ? ' FULL' : '';
  const activity = shell.agentStreamActive ? ' · RUNNING' : '';
  return `${OPERATOR_PERSONA_NAME} · DEBUG${access}${activity}`;
});

const showExpandedPanel = computed(() =>
  ideShowKairoSidebarExpanded(shell.idePresenceProfile),
);

const briefingHeadline = computed(() =>
  briefingPanelHeadline(shell.operatorBriefing, shell.briefingLoadState),
);
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
const showStopSpeech = computed(() => shell.kairoSpeechActive);

function handleExpand(): void {
  if (showStopSpeech.value) {
    shell.stopKairoSpeech();
    return;
  }
  shell.focusKairoBriefing();
}

function handleStopSpeech(event: Event): void {
  event.stopPropagation();
  shell.stopKairoSpeech();
}
</script>

<template>
  <button
    v-if="!showExpandedPanel"
    id="ide-kairo-sidebar-panel"
    type="button"
    class="kairo-sidebar-panel kairo-sidebar-panel--compact"
    :class="[
      `kairo-sidebar-panel--${shell.ideDisplayKairoPresenceState}`,
      {
        'kairo-sidebar-panel--emphasized': shell.briefingSeamEmphasized,
        'kairo-sidebar-panel--debug-mode': debugModeActive,
      },
    ]"
    :aria-label="presenceLabel"
    @click="handleExpand"
  >
    <span class="kairo-sidebar-panel__compact-dot" aria-hidden="true" />
    <span class="kairo-sidebar-panel__compact-label">
      {{ presenceLabel }}
    </span>
  </button>
  <button
    v-else
    id="ide-kairo-sidebar-panel"
    type="button"
    class="kairo-sidebar-panel hud-panel-frame"
    :class="[
      `kairo-sidebar-panel--${shell.kairoPresenceState}`,
      {
        'kairo-sidebar-panel--emphasized': shell.briefingSeamEmphasized,
        'kairo-sidebar-panel--debug-mode': debugModeActive,
      },
    ]"
    :aria-label="`${OPERATOR_PERSONA_NAME}. ${shell.briefingSummaryLine}`"
    @click="handleExpand"
  >
    <p class="kairo-sidebar-panel__title">
      <OperatorPersonaMark size="sm" />
    </p>
    <div class="kairo-sidebar-panel__body">
      <div class="kairo-sidebar-panel__radar" aria-hidden="true">
        <span class="kairo-sidebar-panel__ring kairo-sidebar-panel__ring--outer" />
        <span class="kairo-sidebar-panel__ring kairo-sidebar-panel__ring--mid" />
        <span class="kairo-sidebar-panel__ring kairo-sidebar-panel__ring--inner" />
        <span class="kairo-sidebar-panel__sweep" />
      </div>
      <div class="kairo-sidebar-panel__copy">
        <p class="kairo-sidebar-panel__state">{{ presenceLabel }}</p>
        <AgentLiveLineHeadline
          class="kairo-sidebar-panel__headline"
          :activity="shell.ideComposerActivity"
          :fallback="briefingHeadline"
        />
        <p v-if="shell.briefingSummaryLine" class="kairo-sidebar-panel__summary">
          {{ shell.briefingSummaryLine }}
        </p>
        <p class="kairo-sidebar-panel__notice">{{ notice }}</p>
        <p v-if="advise" class="kairo-sidebar-panel__advise">{{ advise }}</p>
        <div v-if="approvalBadge || signalBadge" class="kairo-sidebar-panel__badges">
          <span v-if="approvalBadge" class="kairo-sidebar-panel__badge">
            {{ approvalBadge }} approval{{ approvalBadge === 1 ? '' : 's' }}
          </span>
          <span v-if="signalBadge" class="kairo-sidebar-panel__badge kairo-sidebar-panel__badge--signal">
            {{ signalBadge }} signal{{ signalBadge === 1 ? '' : 's' }}
          </span>
        </div>
        <button
          v-if="showStopSpeech"
          type="button"
          class="kairo-sidebar-panel__stop-speech"
          @click="handleStopSpeech"
        >
          Stop speaking
        </button>
      </div>
      <section
        v-if="shell.ideComposerActivity?.liveBodyFull"
        class="kairo-sidebar-panel__transcript"
        aria-label="Current run transcript"
      >
        <span class="kairo-sidebar-panel__transcript-label">Run transcript</span>
        <p>{{ shell.ideComposerActivity.liveBodyFull }}</p>
      </section>
      <BriefingSurfaceFollowupPrompt />
    </div>
  </button>
</template>
