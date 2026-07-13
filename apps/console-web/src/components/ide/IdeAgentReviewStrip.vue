<script setup lang="ts">
import { computed, ref } from 'vue';

import type { IdeAgentEditSummary } from '../../lib/ide-agent-center-view';
import {
  buildIdeAgentReviewBar,
  buildIdeAgentReviewComposerLabel,
  collectIdeAgentEditSummariesFromThread,
  latestIdeAgentTurnFailed,
  resolveIdeAgentEditDiffFromThread,
  shouldShowIdeAgentReviewStrip,
} from '../../lib/ide-agent-center-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const expanded = ref(false);

const editSummaries = computed(() =>
  // Stream-safe: path/count metadata only. Diff bodies are resolved on click.
  collectIdeAgentEditSummariesFromThread(shell.threadMessages, { includeDiff: false }),
);

const reviewReadyCount = computed(
  () =>
    shell.runs.filter(
      (run) =>
        run.phase === 'review_ready' &&
        run.workspace_id === shell.currentWorkspace?.workspace_id,
    ).length,
);

const showReviewStrip = computed(() =>
  shouldShowIdeAgentReviewStrip({
    layoutMode: shell.layoutMode,
    agentStreamActive: shell.agentStreamActive,
    composerAgentBusy: shell.composerAgentBusy,
    reviewReadyCount: reviewReadyCount.value,
    editedFileCount: editSummaries.value.length,
    latestAgentTurnFailed: latestIdeAgentTurnFailed(shell.threadMessages),
  }),
);

const reviewBar = computed(() =>
  buildIdeAgentReviewBar({
    canStop: shell.canStopIdeAgentRun,
    stopping: shell.runMutationState === 'stopping',
    editedFileCount: editSummaries.value.length,
    reviewReadyCount: reviewReadyCount.value,
    completing: shell.runMutationState === 'completing',
  }),
);

const canExpandFileList = computed(() => editSummaries.value.length > 0);

const statusLabel = computed(() =>
  buildIdeAgentReviewComposerLabel({
    agentStreamActive: shell.agentStreamActive,
    executionAccess: shell.ideComposerActivity?.executionAccess ?? 'consultative',
    editedFileCount: editSummaries.value.length,
    reviewReadyCount: reviewReadyCount.value,
    expanded: expanded.value,
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
</script>

<template>
  <section
    v-if="showReviewStrip"
    class="ide-agent-review-strip"
    :class="{ 'ide-agent-review-strip--expanded': expanded }"
    aria-label="Agent review controls"
  >
    <div class="ide-agent-review-strip__bar">
      <button
        type="button"
        class="ide-agent-review-strip__toggle"
        :class="{ 'ide-agent-review-strip__toggle--disabled': !canExpandFileList }"
        :disabled="!canExpandFileList"
        :aria-expanded="canExpandFileList ? expanded : undefined"
        @click="toggleExpanded"
      >
        <p class="ide-agent-review-strip__summary">{{ statusLabel }}</p>
      </button>
      <div class="ide-agent-review-strip__actions">
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
