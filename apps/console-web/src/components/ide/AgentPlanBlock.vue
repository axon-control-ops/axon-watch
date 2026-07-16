<script setup lang="ts">
import { computed, ref } from 'vue';

import { buildPlan } from '../../lib/build-plan-action';
import { openPlanInEditor } from '../../lib/open-plan-viewer';
import { displayPlanTitle } from '../../lib/plan-display-title';
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  planId: string;
  title: string;
  workspaceId: string | null;
}>();

const shell = useShellStore();
const opening = ref(false);
const building = ref(false);
const error = ref('');
const cardTitle = computed(() => displayPlanTitle(props.title));
const busy = computed(() => opening.value || building.value);

async function viewPlan(): Promise<void> {
  const workspaceId = props.workspaceId?.trim();
  if (!workspaceId || busy.value) {
    return;
  }
  opening.value = true;
  error.value = '';
  try {
    const opened = await openPlanInEditor({
      shell,
      workspaceId,
      planId: props.planId,
      fallbackTitle: cardTitle.value,
    });
    if (!opened) {
      error.value = 'Plan body was empty.';
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unable to open plan.';
  } finally {
    opening.value = false;
  }
}

async function startBuildPlan(): Promise<void> {
  const workspaceId = props.workspaceId?.trim();
  if (!workspaceId || busy.value) {
    return;
  }
  building.value = true;
  error.value = '';
  try {
    const result = await buildPlan(shell, {
      workspaceId,
      planId: props.planId,
      title: cardTitle.value,
    });
    if (!result.ok) {
      error.value = result.reason;
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unable to build plan.';
  } finally {
    building.value = false;
  }
}
</script>

<template>
  <div class="agent-block agent-block--plan">
    <div class="agent-block__plan-main">
      <span class="agent-block__plan-mark" aria-hidden="true">◈</span>
      <div class="agent-block__plan-copy">
        <p class="agent-block__plan-kicker">Plan saved</p>
        <p class="agent-block__plan-title">{{ cardTitle }}</p>
      </div>
      <div class="agent-block__plan-actions">
        <button
          type="button"
          class="agent-block__plan-view"
          :disabled="!workspaceId || busy"
          @click="viewPlan"
        >
          {{ opening ? 'Opening…' : 'View Plan' }}
        </button>
        <button
          type="button"
          class="agent-block__plan-build"
          :disabled="!workspaceId || busy"
          @click="startBuildPlan"
        >
          {{ building ? 'Building…' : 'Build Plan' }}
        </button>
      </div>
    </div>
    <p
      v-if="error"
      class="agent-block__plan-error"
    >
      {{ error }}
    </p>
  </div>
</template>
