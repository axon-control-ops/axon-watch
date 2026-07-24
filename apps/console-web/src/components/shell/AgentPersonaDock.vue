<script setup lang="ts">
import { computed } from 'vue';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import { buildEmployeeAvatar } from '../../features/workspace-agents/employee-avatar';
import {
  employeeDockDisplayActions,
  type TeamMemberQuickAction,
} from '../../features/workspace-agents/company-roster-actions';
import {
  employeeDisplayStatus,
  employeeDockReceiptDetail,
  employeeDockReceiptRunId,
  employeeDockReceiptRunLabel,
  employeeFailureBeatAriaLabel,
  employeeFailureDetailTooltip,
  employeeFailureLine,
  employeeMetaLine,
  employeeRoleBadge,
  employeeShiftNeedsContinuation,
  employeeStatusLabel,
  employeeTalkLine,
} from '../../features/workspace-agents/company-roster-view';

const props = defineProps<{
  employee: CompanyEmployeeRecord;
  actions: TeamMemberQuickAction[];
  controlBusy: boolean;
}>();

const emit = defineEmits<{
  action: [action: TeamMemberQuickAction];
  talk: [];
}>();

const avatar = computed(() => buildEmployeeAvatar(props.employee));
const failure = computed(() => employeeFailureLine(props.employee));
const interruptedShift = computed(() => employeeShiftNeedsContinuation(props.employee));
const failureDetailTooltip = computed(() => employeeFailureDetailTooltip(props.employee));
const failureBeatAriaLabel = computed(() => employeeFailureBeatAriaLabel(props.employee));
const liveBeat = computed(() => {
  if (failure.value) {
    return failure.value;
  }
  if (!props.employee.enabled) {
    return 'Paused — continuous shifts are off for this teammate.';
  }
  return employeeTalkLine(props.employee) || `${employeeStatusLabel(employeeDisplayStatus(props.employee))} on ${props.employee.owns || 'assigned work'}.`;
});
const receiptDetail = computed(() => employeeDockReceiptDetail(props.employee));
const receiptRunId = computed(() => employeeDockReceiptRunId(props.employee));
const receiptRunLabel = computed(() => employeeDockReceiptRunLabel(receiptRunId.value));
const receiptsAction = computed(() =>
  props.actions.find((action) => action.id === 'receipts') ?? null,
);
const displayActions = computed(() =>
  employeeDockDisplayActions(props.actions, props.employee),
);
</script>

<template>
  <article
    class="agent-persona-dock"
    :class="{ 'agent-persona-dock--interrupted': interruptedShift }"
    :data-presence="avatar.presence"
    :data-role="employee.role"
    :aria-label="`${employee.name} agent dock`"
  >
    <header class="agent-persona-dock__hero">
      <button
        type="button"
        class="agent-persona-dock__avatar-btn"
        :aria-label="`Talk to ${employee.name}`"
        @click="emit('talk')"
      >
        <span
          class="agent-persona-dock__avatar"
          :style="{ background: avatar.background, color: avatar.foreground }"
          :data-glow="avatar.glow"
          :data-presence="avatar.presence"
          :data-lead="avatar.lead ? 'true' : undefined"
        >
          <span
            v-if="avatar.presence === 'working'"
            class="agent-persona-dock__busy-ring"
            aria-hidden="true"
          />
          <img
            class="agent-persona-dock__face"
            :src="avatar.faceUrl"
            :alt="employee.name"
            width="44"
            height="44"
          >
          <span class="agent-persona-dock__initials" aria-hidden="true">{{ avatar.initials }}</span>
          <span
            v-if="avatar.lead"
            class="agent-persona-dock__lead-mark"
            aria-hidden="true"
            title="Lead"
          >
            ★
          </span>
        </span>
      </button>
      <div class="agent-persona-dock__identity">
        <div class="agent-persona-dock__name-row">
          <h4 class="agent-persona-dock__name">{{ employee.name }}</h4>
          <span
            class="company-roster__badge company-roster__badge--role"
            :data-role="employee.role"
          >
            {{ employeeRoleBadge(employee) }}
          </span>
          <span
            v-if="!employee.enabled"
            class="company-roster__badge company-roster__badge--paused"
          >
            Paused
          </span>
        </div>
        <p v-if="employeeMetaLine(employee)" class="agent-persona-dock__meta">
          {{ employeeMetaLine(employee) }}
        </p>
        <p class="agent-persona-dock__owns">{{ employee.owns }}</p>
      </div>
      <span
        class="agent-persona-dock__status"
        :data-status="employeeDisplayStatus(employee)"
      >
        {{ employeeStatusLabel(employeeDisplayStatus(employee)) }}
      </span>
    </header>

    <p
      class="agent-persona-dock__beat"
      :class="{
        'agent-persona-dock__beat--failed': !!failure && !interruptedShift,
        'agent-persona-dock__beat--interrupted': !!failure && interruptedShift,
      }"
      :title="failureDetailTooltip"
      :aria-label="failureBeatAriaLabel ?? undefined"
      :aria-live="failure ? 'polite' : undefined"
      role="status"
    >
      {{ liveBeat }}
    </p>

    <section v-if="receiptDetail || receiptRunId" class="agent-persona-dock__receipt">
      <p class="agent-persona-dock__receipt-label">Last shift</p>
      <p v-if="receiptDetail" class="agent-persona-dock__receipt-detail">
        {{ receiptDetail }}
      </p>
      <p
        v-if="receiptRunId"
        class="agent-persona-dock__receipt-run"
      >
        <button
          v-if="receiptsAction"
          type="button"
          class="agent-persona-dock__receipt-run-btn"
          :title="receiptRunId"
          :aria-label="`Explain receipts for ${receiptRunLabel || receiptRunId}`"
          @click="emit('action', receiptsAction)"
        >
          {{ receiptRunLabel || receiptRunId }}
        </button>
        <span v-else :title="receiptRunId">{{ receiptRunLabel || receiptRunId }}</span>
      </p>
    </section>

    <div
      v-if="displayActions.length"
      class="agent-persona-dock__actions"
      role="group"
      :aria-label="`Actions for ${employee.name}`"
    >
      <button
        v-for="action in displayActions"
        :key="action.id"
        type="button"
        class="company-roster__action"
        :class="{
          'company-roster__action--surface': action.kind === 'surface',
          'company-roster__action--retry': action.id === 'retry',
          'company-roster__action--receipts': action.id === 'receipts',
          'company-roster__action--control': action.kind === 'control',
        }"
        :disabled="controlBusy && action.kind === 'control'"
        @click="emit('action', action)"
      >
        {{ action.label }}
      </button>
    </div>
  </article>
</template>
