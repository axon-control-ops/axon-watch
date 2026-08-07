<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';

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
  employeeTalkLineDetailTooltip,
} from '../../features/workspace-agents/company-roster-view';
import { resolveEmployeeDeliveryLinks } from '../../features/workspace-agents/employee-delivery-handoff-view';

const props = defineProps<{
  employee: CompanyEmployeeRecord;
  actions: TeamMemberQuickAction[];
  controlBusy: boolean;
  liveBusy?: boolean;
  handoffWaiting?: boolean;
  /** True while THIS employee's own thread is the one live-streaming right
   * now — reveals `transcript` while the roster stays available. */
  reporting?: boolean;
  /** Full live/latest reply text for this employee's active turn. Only
   * meaningful (and only rendered) while `reporting` is true. */
  transcript?: string;
}>();

const emit = defineEmits<{
  action: [action: TeamMemberQuickAction];
  talk: [];
}>();

const avatar = computed(() =>
  buildEmployeeAvatar(props.employee, {
    liveBusy: props.liveBusy,
    handoffWaiting: props.handoffWaiting,
  }),
);
const failure = computed(() =>
  employeeFailureLine(props.employee, { liveBusy: props.liveBusy }),
);
const interruptedShift = computed(() =>
  Boolean(failure.value) && employeeShiftNeedsContinuation(props.employee),
);
const failureDetailTooltip = computed(() => employeeFailureDetailTooltip(props.employee));
const failureBeatAriaLabel = computed(() => employeeFailureBeatAriaLabel(props.employee));
const beatDetailTooltip = computed(
  () => failureDetailTooltip.value || employeeTalkLineDetailTooltip(props.employee),
);
const deliveryLinks = computed(() =>
  resolveEmployeeDeliveryLinks({
    stage: props.employee.pipeline_stage,
    detail: props.employee.pipeline_detail,
    draftPrUrl: props.employee.draft_pr_url,
    ciRunUrl: props.employee.ci_run_url,
    ciStatus: props.employee.ci_status,
  }),
);
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

const transcriptRef = ref<HTMLElement | null>(null);

// Follow the stream: keep the newest text in view as it grows, matching the
// terminal/chat convention rather than leaving the operator scrolled to the
// top of a card that's still filling in.
watch(
  () => props.transcript,
  () => {
    void nextTick(() => {
      const target = transcriptRef.value;
      if (!target) {
        return;
      }
      target.scrollTop = target.scrollHeight;
    });
  },
);
</script>

<template>
  <article
    class="agent-persona-dock"
    :class="{
      'agent-persona-dock--interrupted': interruptedShift,
      'agent-persona-dock--reporting': reporting,
    }"
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
            v-if="avatar.presence === 'working' || avatar.presence === 'handoff'"
            class="agent-persona-dock__busy-ring"
            :class="{ 'agent-persona-dock__busy-ring--handoff': avatar.presence === 'handoff' }"
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
      :title="beatDetailTooltip ?? undefined"
      :aria-label="failureBeatAriaLabel ?? undefined"
      :aria-live="failure ? 'polite' : undefined"
      role="status"
    >
      {{ liveBeat }}
    </p>

    <div
      v-if="reporting && transcript"
      ref="transcriptRef"
      class="agent-persona-dock__transcript"
      aria-label="Live report transcript"
      aria-live="polite"
    >{{ transcript }}</div>

    <div
      v-if="deliveryLinks"
      class="agent-persona-dock__delivery-links"
      aria-label="Open pull request and CI"
    >
      <a
        v-if="deliveryLinks.draftPrUrl"
        class="agent-persona-dock__delivery-link"
        :href="deliveryLinks.draftPrUrl"
        target="_blank"
        rel="noopener noreferrer"
      >
        {{
          deliveryLinks.prNumber
            ? `Open PR #${deliveryLinks.prNumber}`
            : 'Open draft PR'
        }}
        <template v-if="deliveryLinks.running"> · running</template>
      </a>
      <a
        v-if="deliveryLinks.ciRunUrl"
        class="agent-persona-dock__delivery-link"
        :href="deliveryLinks.ciRunUrl"
        target="_blank"
        rel="noopener noreferrer"
      >
        Watch CI
      </a>
    </div>

    <section v-if="receiptDetail || receiptRunId" class="agent-persona-dock__receipt">
      <p class="agent-persona-dock__receipt-label">Last job</p>
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
          :aria-label="`Explain what happened for ${receiptRunLabel || receiptRunId}`"
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
          'company-roster__action--start-now': action.id === 'start_now',
        }"
        :disabled="controlBusy && action.kind === 'control'"
        @click="emit('action', action)"
      >
        {{ action.label }}
      </button>
    </div>
  </article>
</template>
