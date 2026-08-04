<script setup lang="ts">
import { computed, nextTick, onMounted, onUpdated, ref } from 'vue';

import type { IdeAgentEditSummary } from '../../lib/ide-agent-center-view';
import {
  buildIdeAgentReviewBar,
  buildIdeAgentReviewComposerLabel,
  collectIdeAgentEditSummariesFromThread,
  extractIdeAgentEditSummaries,
  latestIdeAgentTurnFailed,
  latestIdeAgentTurnHasConfidence,
  resolveActiveIdeAgentMessage,
  resolveIdeAgentEditDiffFromThread,
  shouldShowIdeAgentReviewStrip,
} from '../../lib/ide-agent-center-view';
import { composerRuntimeFamilyLabel } from '../../lib/cursor-catalog-view';
import { useEmployeeFailureStripActions } from '../../composables/agent-dock/use-employee-failure-strip-actions';
import { runContinueActionLabel } from '../../lib/run-lifecycle-ui';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const expanded = ref(false);
const stripBarRef = ref<HTMLElement | null>(null);
const runtimeChipRef = ref<HTMLElement | null>(null);

const {
  retrying,
  showFailureActions,
  showRetryAction,
  showExplainAction,
  interruptedShift,
  retryLabel,
  actionsDisabled,
  handleRetry,
  handleExplain,
  handleOpenTeam,
} = useEmployeeFailureStripActions(shell);

const runtimeFamilyLabel = computed(() => {
  const preferred = shell.selectedRuntimeTargetId;
  const status = shell.runtimeStatus;
  const records = status ? [...status.local, ...status.cloud] : [];
  const selected =
    (preferred ? records.find((row) => row.id === preferred) : null) ??
    (status?.default_runtime
      ? records.find((row) => row.id === status.default_runtime)
      : null) ??
    records[0] ??
    null;
  return composerRuntimeFamilyLabel(selected?.family ?? 'cursor');
});

const editSummaries = computed(() => {
  // During an active stream, avoid full-transcript rescans — use incremental edit count.
  if (shell.agentStreamActive) {
    return [];
  }
  const messages = shell.threadMessages;
  // Successful close-out (incl. Lead handoff Confidence) must not resurrect
  // Review-N-files chrome from older agent turns on the same thread.
  if (latestIdeAgentTurnHasConfidence(messages)) {
    const latest = resolveActiveIdeAgentMessage(messages, false, null);
    if (!latest) {
      return [];
    }
    return extractIdeAgentEditSummaries(latest.content, latest.message_id, {
      includeDiff: false,
    });
  }
  return collectIdeAgentEditSummariesFromThread(messages, { includeDiff: false });
});

const streamedEditCount = computed(
  () => shell.ideComposerActivity?.streamCounts?.edit ?? 0,
);

const editedFileCount = computed(() =>
  shell.agentStreamActive
    ? Math.max(streamedEditCount.value, editSummaries.value.length)
    : editSummaries.value.length,
);

const reviewReadyCount = computed(
  () =>
    shell.runs.filter(
      (run) =>
        run.phase === 'review_ready' &&
        run.workspace_id === shell.currentWorkspace?.workspace_id,
    ).length,
);

const showReviewControls = computed(() =>
  shouldShowIdeAgentReviewStrip({
    layoutMode: shell.layoutMode,
    agentStreamActive: shell.agentStreamActive,
    composerAgentBusy: shell.composerAgentBusy,
    reviewReadyCount: reviewReadyCount.value,
    editedFileCount: editedFileCount.value,
    latestAgentTurnFailed: latestIdeAgentTurnFailed(shell.threadMessages),
    employeeFailureActions: showFailureActions.value,
  }) || shell.canResumeIdeAgentRun,
);

const showReviewStrip = computed(
  () => showReviewControls.value,
);

const reviewBar = computed(() =>
  buildIdeAgentReviewBar({
    canStop: shell.canStopIdeAgentRun,
    stopping: shell.runMutationState === 'stopping',
    canResume: shell.canResumeIdeAgentRun,
    resuming: shell.runMutationState === 'resuming',
    resumeLabel: runContinueActionLabel({
      phase: shell.ideAgentLinkedRun?.phase,
      agentStreamActive: shell.agentStreamActive,
      mode: shell.ideAgentLinkedRun?.mode,
      continueLabel: 'Continue',
      resumeLabel: 'Resume',
    }),
    editedFileCount: editedFileCount.value,
    reviewReadyCount: reviewReadyCount.value,
    completing: shell.runMutationState === 'completing',
  }),
);

const canExpandFileList = computed(() => editSummaries.value.length > 0);

const statusLabel = computed(() =>
  buildIdeAgentReviewComposerLabel({
    agentStreamActive: shell.agentStreamActive,
    executionAccess: shell.ideComposerActivity?.executionAccess ?? 'consultative',
    editedFileCount: editedFileCount.value,
    reviewReadyCount: reviewReadyCount.value,
    expanded: expanded.value,
    mode: shell.ideComposerActivity?.mode,
  }),
);

function toggleExpanded(): void {
  if (!canExpandFileList.value) {
    return;
  }
  expanded.value = !expanded.value;
}

function stopAgentRun(): void {
  void shell.stopIdeAgentRun();
}

function resumeAgentRun(): void {
  void shell.resumeIdeAgentRun();
}

function applyAllReviewReady(): void {
  void shell.completeAllReviewReadyRuns();
}

function openEditPath(edit: IdeAgentEditSummary): void {
  const diff = edit.diff || resolveIdeAgentEditDiffFromThread(shell.threadMessages, edit.path);
  shell.openAgentEditReview({
    ...edit,
    diff,
  });
}

function focusReviewFiles(): void {
  const first = editSummaries.value[0];
  if (!first) {
    return;
  }
  expanded.value = true;
  openEditPath(first);
}

function probeRuntimeChipCenter(): void {
  const bar = stripBarRef.value;
  const chip = runtimeChipRef.value;
  if (!bar || !chip) {
    return;
  }
  const barRect = bar.getBoundingClientRect();
  const chipRect = chip.getBoundingClientRect();
  const barMid = barRect.left + barRect.width / 2;
  const chipMid = chipRect.left + chipRect.width / 2;
  const offsetPx = Math.round(chipMid - barMid);
  const computedPos = window.getComputedStyle(chip).position;
  const barDisplay = window.getComputedStyle(bar).display;
  const distToRightPx = Math.round(barRect.right - chipRect.right);
  const distToLeftPx = Math.round(chipRect.left - barRect.left);
  // #region agent log
  fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Debug-Session-Id': 'bef50e',
    },
    body: JSON.stringify({
      sessionId: 'bef50e',
      runId: 'cursor-chip-center-grid',
      hypothesisId: 'H-GRID',
      location: 'IdeAgentReviewStrip.vue:probeRuntimeChipCenter',
      message: 'runtime chip vs strip midpoint (grid center cell)',
      data: {
        offsetPx,
        centered: Math.abs(offsetPx) <= 4,
        barWidth: Math.round(barRect.width),
        chipWidth: Math.round(chipRect.width),
        computedPos,
        barDisplay,
        distToLeftPx,
        distToRightPx,
        label: runtimeFamilyLabel.value,
        showControls: showReviewControls.value,
        chipClass: String(chip.className),
      },
      timestamp: Date.now(),
    }),
  }).catch(() => {});
  // #endregion
}

onMounted(() => {
  void nextTick(() => probeRuntimeChipCenter());
});

onUpdated(() => {
  void nextTick(() => probeRuntimeChipCenter());
});
</script>

<template>
  <section
    v-if="showReviewStrip"
    class="ide-agent-review-strip"
    :class="{
      'ide-agent-review-strip--expanded': expanded,
      'ide-agent-review-strip--attention': showFailureActions,
      'ide-agent-review-strip--interrupted': interruptedShift,
    }"
    aria-label="Agent review controls"
  >
    <div
      ref="stripBarRef"
      class="ide-agent-review-strip__bar"
    >
      <div class="ide-agent-review-strip__side ide-agent-review-strip__side--start">
        <button
          v-if="showReviewControls"
          type="button"
          class="ide-agent-review-strip__toggle"
          :class="{ 'ide-agent-review-strip__toggle--disabled': !canExpandFileList }"
          :disabled="!canExpandFileList"
          :aria-expanded="canExpandFileList ? expanded : undefined"
          @click="toggleExpanded"
        >
          <p class="ide-agent-review-strip__summary">{{ statusLabel }}</p>
        </button>
      </div>
      <div class="ide-agent-review-strip__side ide-agent-review-strip__side--center">
        <span
          ref="runtimeChipRef"
          class="ide-agent-review-strip__runtime"
          :title="`CLI runtime: ${runtimeFamilyLabel}`"
        >{{ runtimeFamilyLabel }}</span>
      </div>
      <div class="ide-agent-review-strip__side ide-agent-review-strip__side--end">
        <div v-if="showReviewControls" class="ide-agent-review-strip__actions">
          <button
            v-if="showRetryAction"
            type="button"
            class="ide-agent-review-strip__btn ide-agent-review-strip__btn--retry"
            :disabled="actionsDisabled"
            :title="`${retryLabel} this teammate's last job`"
            @click="handleRetry"
          >
            {{ retrying ? 'Working…' : retryLabel }}
          </button>
          <button
            v-if="showFailureActions && showExplainAction"
            type="button"
            class="ide-agent-review-strip__btn ide-agent-review-strip__btn--link"
            title="Opens Ask so they explain what happened without changing code"
            :disabled="actionsDisabled"
            @click="handleExplain"
          >
            Explain
          </button>
          <button
            v-if="showFailureActions"
            type="button"
            class="ide-agent-review-strip__btn ide-agent-review-strip__btn--link"
            @click="handleOpenTeam"
          >
            Open team
          </button>
          <button
            v-if="reviewBar.showStop"
            type="button"
            class="ide-agent-review-strip__btn ide-agent-review-strip__btn--stop"
            :disabled="shell.runMutationState === 'stopping'"
            @click="stopAgentRun"
          >
            {{ reviewBar.stopLabel }}
          </button>
          <button
            v-if="reviewBar.showResume"
            type="button"
            class="ide-agent-review-strip__btn ide-agent-review-strip__btn--resume"
            :disabled="shell.runMutationState === 'resuming'"
            @click="resumeAgentRun"
          >
            {{ reviewBar.resumeLabel }}
          </button>
          <button
            v-if="reviewBar.showReview"
            type="button"
            class="ide-agent-review-strip__btn ide-agent-review-strip__btn--review"
            @click="focusReviewFiles"
          >
            {{ reviewBar.reviewLabel }}
          </button>
          <button
            v-if="reviewBar.showApplyAll"
            type="button"
            class="ide-agent-review-strip__btn ide-agent-review-strip__btn--apply"
            :disabled="shell.runMutationState === 'completing'"
            @click="applyAllReviewReady"
          >
            {{ reviewBar.applyLabel }}
          </button>
        </div>
      </div>
    </div>

    <ul
      v-if="expanded && editSummaries.length"
      class="ide-agent-review-strip__files"
      aria-label="Changed files"
    >
      <li
        v-for="edit in editSummaries"
        :key="edit.id"
        class="ide-agent-review-strip__file"
      >
        <button
          type="button"
          class="ide-agent-review-strip__file-btn"
          :title="`Open ${edit.path} in editor`"
          @click="openEditPath(edit)"
        >
          <span class="ide-agent-review-strip__file-path">{{ edit.path }}</span>
          <span class="ide-agent-review-strip__file-stat ide-agent-review-strip__file-stat--add">
            +{{ edit.added }}
          </span>
          <span
            v-if="edit.removed > 0"
            class="ide-agent-review-strip__file-stat ide-agent-review-strip__file-stat--remove"
          >
            -{{ edit.removed }}
          </span>
        </button>
      </li>
    </ul>
  </section>
</template>
