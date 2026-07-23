<script setup lang="ts">
import { computed, ref } from 'vue';

import type { LeadTaskPlan } from '../../api/lead-planner-api';
import {
  confirmLeadDelegation,
  previewLeadDelegation,
} from '../../lib/delegate-lead-plan-action';
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
const reviewing = ref(false);
const delegating = ref(false);
const error = ref('');
const status = ref('');
const previewPlan = ref<LeadTaskPlan | null>(null);
const cardTitle = computed(() => displayPlanTitle(props.title));
const busy = computed(
  () => opening.value || building.value || reviewing.value || delegating.value,
);
const isLeadThread = computed(() => {
  const role = String(shell.activeIdeEmployeeRecord?.role || '').trim().toLowerCase();
  return role === 'lead';
});

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
  status.value = '';
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

async function reviewTeamTasks(): Promise<void> {
  const workspaceId = props.workspaceId?.trim();
  if (!workspaceId || busy.value) {
    return;
  }
  reviewing.value = true;
  error.value = '';
  status.value = '';
  try {
    const attachmentIds = (shell.threadMessages || [])
      .flatMap((message) => message.attachments ?? [])
      .map((attachment) => String(attachment.attachment_id || '').trim())
      .filter(Boolean);
    const result = await previewLeadDelegation({
      workspaceId,
      planId: props.planId,
      title: cardTitle.value,
      attachmentIds,
    });
    if (!result.ok) {
      error.value = result.reason;
      previewPlan.value = result.preview ?? null;
      return;
    }
    previewPlan.value = result.preview;
    status.value = `Preview ready: ${result.taskCount} task(s). Confirm to materialize.`;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unable to preview team tasks.';
  } finally {
    reviewing.value = false;
  }
}

async function confirmDelegation(): Promise<void> {
  const workspaceId = props.workspaceId?.trim();
  if (!workspaceId || busy.value || !previewPlan.value) {
    return;
  }
  const confirmed = window.confirm(
    [
      'Delegate these Lead tasks?',
      '',
      ...previewPlan.value.items.map(
        (item) =>
          `- ${item.assignee_name || item.owner_role}: ${item.goal.slice(0, 120)}` +
          (item.attachment_ids?.length ? ` [${item.attachment_ids.length} attachment(s)]` : ''),
      ),
      '',
      'Scheduler stays off. Ready runs are created for operator/worker follow-up.',
    ].join('\n'),
  );
  if (!confirmed) {
    return;
  }
  delegating.value = true;
  error.value = '';
  try {
    const attachmentIds = (shell.threadMessages || [])
      .flatMap((message) => message.attachments ?? [])
      .map((attachment) => String(attachment.attachment_id || '').trim())
      .filter(Boolean);
    const result = await confirmLeadDelegation({
      workspaceId,
      planId: props.planId,
      title: cardTitle.value,
      attachmentIds,
      dispatchWorkers: false,
    });
    if (!result.ok) {
      error.value = result.reason;
      return;
    }
    previewPlan.value = result.preview;
    status.value = `Delegated ${result.taskCount} task(s); ${result.runCount} ready run(s). Plan ${result.planId}.`;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unable to delegate team tasks.';
  } finally {
    delegating.value = false;
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
        <button
          v-if="isLeadThread"
          type="button"
          class="agent-block__plan-view"
          :disabled="!workspaceId || busy"
          @click="reviewTeamTasks"
        >
          {{ reviewing ? 'Reviewing…' : 'Review team tasks' }}
        </button>
        <button
          v-if="isLeadThread && previewPlan"
          type="button"
          class="agent-block__plan-build"
          :disabled="!workspaceId || busy"
          @click="confirmDelegation"
        >
          {{ delegating ? 'Delegating…' : 'Delegate' }}
        </button>
      </div>
    </div>
    <ul
      v-if="previewPlan?.items?.length"
      class="agent-block__plan-preview"
    >
      <li
        v-for="item in previewPlan.items"
        :key="item.plan_key"
      >
        <strong>{{ item.assignee_name || item.owner_role }}</strong>
        — {{ item.goal }}
        <span
          v-if="item.attachment_ids?.length"
          class="agent-block__plan-preview-meta"
        >
          · {{ item.attachment_ids.length }} attachment(s)
        </span>
      </li>
    </ul>
    <p
      v-if="status"
      class="agent-block__plan-status"
    >
      {{ status }}
    </p>
    <p
      v-if="error"
      class="agent-block__plan-error"
    >
      {{ error }}
    </p>
  </div>
</template>
