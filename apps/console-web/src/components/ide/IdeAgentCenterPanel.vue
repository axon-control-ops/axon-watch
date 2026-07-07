<script setup lang="ts">
import { computed, ref } from 'vue';

import { diffLineTone, thinkingPreview } from '../../lib/agent-transcript-blocks';
import { summarizeIdeAgentActivity } from '../../lib/ide-agent-activity-view';
import {
  buildIdeAgentReviewBar,
  extractIdeAgentEditSummaries,
  resolveActiveIdeAgentMessage,
} from '../../lib/ide-agent-center-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const collapsedEditKeys = ref<Record<string, boolean>>({});

const activeAgentMessage = computed(() =>
  resolveActiveIdeAgentMessage(
    shell.threadMessages,
    shell.agentStreamActive,
    shell.agentStreamMessageId,
  ),
);

const editSummaries = computed(() => {
  const message = activeAgentMessage.value;
  if (!message) {
    return [];
  }
  return extractIdeAgentEditSummaries(message.content, message.message_id);
});

const activitySummary = computed(() =>
  summarizeIdeAgentActivity(activeAgentMessage.value?.content ?? ''),
);

const reviewReadyCount = computed(
  () =>
    shell.runs.filter(
      (run) =>
        run.phase === 'review_ready' &&
        run.workspace_id === shell.currentWorkspace?.workspace_id,
    ).length,
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

const statusLabel = computed(() => {
  if (shell.agentStreamActive) {
    return shell.ideComposerActivity?.label ?? 'Agent is working…';
  }
  if (reviewReadyCount.value > 0) {
    return 'Review the agent changes, then apply or complete the run.';
  }
  return 'Agent finished — review file changes below.';
});

const isStreaming = computed(
  () =>
    shell.agentStreamActive &&
    activeAgentMessage.value?.message_id === shell.agentStreamMessageId,
);

function isEditExpanded(editId: string): boolean {
  return !(collapsedEditKeys.value[editId] ?? false);
}

function toggleEdit(editId: string): void {
  collapsedEditKeys.value = {
    ...collapsedEditKeys.value,
    [editId]: isEditExpanded(editId),
  };
}

function diffLines(diff: string): Array<{ text: string; tone: string }> {
  return diff.split('\n').map((line) => ({ text: line, tone: diffLineTone(line) }));
}

function openEditPath(path: string): void {
  void shell.openWorkspaceFile(path);
}

function stopAgentRun(): void {
  void shell.stopIdeAgentRun();
}

function applyAllReviewReady(): void {
  void shell.completeAllReviewReadyRuns();
}

function focusReviewFiles(): void {
  const first = editSummaries.value[0];
  if (!first) {
    return;
  }
  collapsedEditKeys.value = {
    ...collapsedEditKeys.value,
    [first.id]: false,
  };
  void shell.openWorkspaceFile(first.path);
}

function revealTerminalPanel(): void {
  shell.revealIdeTerminalPanel();
}
</script>

<template>
  <section class="ide-agent-center-panel hud-panel-frame" aria-label="Agent progress">
    <header class="ide-agent-center-panel__review-bar">
      <div class="ide-agent-center-panel__review-copy">
        <p class="ide-agent-center-panel__eyebrow">Agent workbench</p>
        <p class="ide-agent-center-panel__status">{{ statusLabel }}</p>
      </div>
      <div class="ide-agent-center-panel__review-actions">
        <button
          v-if="reviewBar.showStop"
          type="button"
          class="ide-agent-center-panel__btn ide-agent-center-panel__btn--stop"
          :disabled="shell.runMutationState === 'stopping'"
          @click="stopAgentRun"
        >
          {{ reviewBar.stopLabel }}
        </button>
        <button
          v-if="reviewBar.showReview"
          type="button"
          class="ide-agent-center-panel__btn ide-agent-center-panel__btn--review"
          @click="focusReviewFiles"
        >
          {{ reviewBar.reviewLabel }}
        </button>
        <button
          v-if="reviewBar.showApplyAll"
          type="button"
          class="ide-agent-center-panel__btn ide-agent-center-panel__btn--apply"
          :disabled="shell.runMutationState === 'completing'"
          @click="applyAllReviewReady"
        >
          {{ reviewBar.applyLabel }}
        </button>
      </div>
    </header>

    <div
      v-if="activitySummary.chips.length"
      class="ide-agent-center-panel__activity"
      aria-label="Live agent activity"
    >
      <button
        v-for="chip in activitySummary.chips"
        :key="chip.id"
        type="button"
        class="ide-agent-center-panel__activity-chip"
        :class="`ide-agent-center-panel__activity-chip--${chip.kind}`"
        :disabled="chip.kind !== 'terminal'"
        @click="chip.kind === 'terminal' ? revealTerminalPanel() : undefined"
      >
        {{ chip.label }}
      </button>
    </div>

    <div class="ide-agent-center-panel__body">
      <p v-if="!editSummaries.length && isStreaming" class="ide-agent-center-panel__empty region-copy">
        Waiting for file edits…
      </p>
      <p
        v-else-if="!editSummaries.length"
        class="ide-agent-center-panel__empty region-copy"
      >
        No file diffs in the latest agent turn yet.
      </p>

      <article
        v-for="edit in editSummaries"
        :key="edit.id"
        class="ide-agent-center-panel__edit agent-block agent-block--edit"
      >
        <div class="agent-block__edit-header">
          <button
            type="button"
            class="agent-block__edit-toggle"
            @click="toggleEdit(edit.id)"
          >
            <span class="agent-block__edit-icon" aria-hidden="true">
              {{ isEditExpanded(edit.id) ? '▾' : '▸' }}
            </span>
          </button>
          <button
            type="button"
            class="agent-block__edit-path agent-block__edit-path--link"
            :title="`Open ${edit.path} in editor`"
            @click="openEditPath(edit.path)"
          >
            {{ edit.path }}
          </button>
          <span class="agent-block__edit-stat agent-block__edit-stat--add">+{{ edit.added }}</span>
          <span class="agent-block__edit-stat agent-block__edit-stat--remove">-{{ edit.removed }}</span>
          <span
            v-if="edit.open && isStreaming"
            class="ide-agent-center-panel__edit-live"
          >
            editing…
          </span>
        </div>
        <pre
          v-if="isEditExpanded(edit.id) && edit.diff"
          class="agent-block__edit-diff ide-agent-center-panel__edit-diff"
        ><span
          v-for="(diffLine, diffIndex) in diffLines(edit.diff)"
          :key="diffIndex"
          class="agent-block__diff-line"
          :class="`agent-block__diff-line--${diffLine.tone}`"
        >{{ diffLine.text }}
</span></pre>
        <p
          v-else-if="isEditExpanded(edit.id) && edit.open && isStreaming"
          class="ide-agent-center-panel__edit-pending region-copy"
        >
          {{ thinkingPreview('Diff still streaming…', 48) }}
        </p>
      </article>
    </div>
  </section>
</template>
