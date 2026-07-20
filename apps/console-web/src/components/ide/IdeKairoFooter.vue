<script setup lang="ts">
import { computed } from 'vue';

import KairoChip from '../KairoChip.vue';
import OperatorPersonaMark from '../OperatorPersonaMark.vue';
import AgentLiveLineHeadline from './AgentLiveLineHeadline.vue';
import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import {
  briefingAdvise,
  briefingNotice,
  briefingPanelHeadline,
} from '../../lib/briefing-panel-view';
import { kairoPresenceLabel } from '../../lib/kairo-presence';
import {
  ideShowKairoSidebarExpanded,
  resolveIdeKairoChipState,
  shouldSurfaceIdeEmployeeFailure,
} from '../../lib/ide-presence-profile';
import { employeeFailureDetailTooltip } from '../../features/workspace-agents/company-roster-view';
import { useShellStore } from '../../stores/shell';
import BriefingSurfaceFollowupPrompt from '../../features/kairo-conversation/BriefingSurfaceFollowupPrompt.vue';

const shell = useShellStore();

const showExpandedPanel = computed(() =>
  ideShowKairoSidebarExpanded(shell.idePresenceProfile),
);

const activePersonaName = computed(
  () => shell.activeIdeEmployee?.name?.trim() || OPERATOR_PERSONA_NAME,
);
const activePersonaMark = computed(() => shell.activeIdeEmployee?.initials ?? null);
const chipState = computed(() =>
  resolveIdeKairoChipState({
    profileState: shell.ideDisplayKairoPresenceState,
    employeeFailureLine: shell.activeIdeEmployeeFailureLine,
    agentStreamActive: shell.agentStreamActive,
    kairoSpeechActive: shell.kairoSpeechActive,
  }),
);
const surfaceEmployeeFailure = computed(() =>
  shouldSurfaceIdeEmployeeFailure({
    profileState: shell.ideDisplayKairoPresenceState,
    employeeFailureLine: shell.activeIdeEmployeeFailureLine,
    agentStreamActive: shell.agentStreamActive,
    kairoSpeechActive: shell.kairoSpeechActive,
  }),
);
const chipEmployeeFailed = computed(() => surfaceEmployeeFailure.value);
const chipPresenceHint = computed(() =>
  chipEmployeeFailed.value ? 'last shift failed' : null,
);
const chipTitle = computed(() => {
  const row = shell.activeIdeEmployeeRecord;
  if (!row || !chipEmployeeFailed.value) {
    return null;
  }
  return employeeFailureDetailTooltip(row) ?? shell.activeIdeEmployeeFailureLine;
});
const chipOpenHint = computed(() =>
  chipEmployeeFailed.value ? 'Open team roster for retry and receipts' : null,
);

function handleKairoPresenceOpen(): void {
  if (chipEmployeeFailed.value) {
    shell.revealTeamRosterForActiveEmployee();
    return;
  }
  shell.focusKairoBriefing();
}

const presenceStateLabel = computed(() =>
  kairoPresenceLabel(shell.kairoPresenceState, activePersonaName.value),
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
</script>

<template>
  <footer class="ide-kairo-footer" :aria-label="`${activePersonaName} presence`">
    <KairoChip
      v-if="!showExpandedPanel"
      class="ide-kairo-footer__chip"
      :state="chipState"
      :persona-mark="activePersonaMark"
      :persona-name="shell.activeIdeEmployee ? activePersonaName : null"
      :presence-hint="chipPresenceHint"
      :employee-failed="chipEmployeeFailed"
      :chip-title="chipTitle"
      :open-hint="chipOpenHint"
      @open-briefing="handleKairoPresenceOpen"
    />
    <BriefingSurfaceFollowupPrompt v-if="!showExpandedPanel" compact />
    <button
      v-else
      id="ide-kairo-footer-panel"
      type="button"
      class="ide-kairo-footer__interrupt hud-panel-frame"
      :class="[
        `ide-kairo-footer__interrupt--${shell.kairoPresenceState}`,
        {
          'ide-kairo-footer__interrupt--emphasized': shell.briefingSeamEmphasized,
          'ide-kairo-footer__interrupt--employee-failed': chipEmployeeFailed,
        },
      ]"
      :aria-label="`${activePersonaName}. ${shell.briefingSummaryLine}`"
      @click="handleKairoPresenceOpen"
    >
      <div class="ide-kairo-footer__interrupt-head">
        <span class="ide-kairo-footer__interrupt-title">
          <OperatorPersonaMark size="sm" :mark="activePersonaMark" />
        </span>
        <span class="ide-kairo-footer__interrupt-state">
          {{
            chipEmployeeFailed && chipPresenceHint
              ? `${activePersonaName} · ${chipPresenceHint}`
              : presenceStateLabel
          }}
        </span>
      </div>
      <p
        v-if="chipEmployeeFailed && shell.activeIdeEmployeeFailureLine"
        class="ide-kairo-footer__employee-failure"
        :title="chipTitle ?? undefined"
      >
        {{ shell.activeIdeEmployeeFailureLine }}
      </p>
      <AgentLiveLineHeadline
        class="ide-kairo-footer__interrupt-headline"
        :activity="shell.ideComposerActivity"
        :fallback="briefingHeadline"
      />
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
      <BriefingSurfaceFollowupPrompt compact />
    </button>
  </footer>
</template>
