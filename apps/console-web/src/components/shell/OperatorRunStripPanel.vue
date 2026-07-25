<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import { buildOperatorRunStripView } from '../../lib/operator-run-strip-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const expanded = ref<boolean | null>(null);

const reviewReadyRuns = computed(() =>
  shell.runs.filter(
    (run) =>
      run.phase === 'review_ready' &&
      run.workspace_id === shell.currentWorkspace?.workspace_id,
  ),
);

const stripView = computed(() =>
  buildOperatorRunStripView({
    reviewReadyRuns: reviewReadyRuns.value,
    expanded: expanded.value ?? undefined,
  }),
);

watch(
  () => [stripView.value.defaultExpanded, stripView.value.totalCount] as const,
  () => {
    expanded.value = null;
  },
);

function toggleExpanded(): void {
  expanded.value = !(expanded.value ?? stripView.value.defaultExpanded);
}

const isExpanded = computed(
  () => expanded.value ?? stripView.value.defaultExpanded,
);
</script>

<template>
  <section
    v-if="stripView.showStrip"
    class="operator-run-strip"
    :class="{
      'operator-run-strip--collapsed': !isExpanded,
      'operator-run-strip--auto-complete': stripView.allAutoComplete,
    }"
    aria-label="Run queue strip"
  >
    <header class="operator-run-strip__header">
      <button
        type="button"
        class="operator-run-strip__toggle"
        :aria-expanded="isExpanded"
        @click="toggleExpanded"
      >
        <span class="operator-run-strip__headline">{{ stripView.headline }}</span>
        <span class="operator-run-strip__chevron">{{ isExpanded ? '▾' : '▸' }}</span>
      </button>
      <button
        type="button"
        class="operator-run-strip__complete"
        :disabled="shell.runMutationPending"
        @click="shell.completeAllReviewReadyRuns()"
      >
        {{
          shell.runMutationState === 'completing' ? 'Completing…' : stripView.completeAllLabel
        }}
      </button>
    </header>

    <p class="operator-run-strip__detail">{{ stripView.detail }}</p>

    <ul v-if="isExpanded" class="operator-run-strip__groups">
      <li
        v-for="group in stripView.groups"
        :key="group.key"
        class="operator-run-strip__group"
      >
        <span class="operator-run-strip__group-label">
          {{ group.label }}
          <span v-if="group.count > 1" class="operator-run-strip__group-count">
            ×{{ group.count }}
          </span>
        </span>
        <span v-if="group.autoComplete" class="operator-run-strip__group-tag">one-shot</span>
      </li>
    </ul>
  </section>
</template>
