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
  employeeRuntimeShiftHint,
  employeeShiftNeedsContinuation,
  employeeStatusLabel,
  employeeTalkLine,
  employeeTalkLineDetailTooltip,
} from '../../features/workspace-agents/company-roster-view';
import {
  APPROVE_PENDING_RECOVERY_ID,
  failedShiftSubjectFromDecisionTitle,
  pendingDecisionCardOptions,
  pendingDecisionPrompt as resolvePendingDecisionPrompt,
} from '../../features/workspace-agents/company-roster-focus';
import { resolveEmployeeDeliveryLinks } from '../../features/workspace-agents/employee-delivery-handoff-view';
import {
  buildTeamPanelTranscriptLines,
  type TeamPanelTranscriptLine,
} from '../../lib/team-panel-transcript-view';

const props = defineProps<{
  employee: CompanyEmployeeRecord;
  actions: TeamMemberQuickAction[];
  controlBusy: boolean;
  liveBusy?: boolean;
  handoffWaiting?: boolean;
  /** Short hint while a headless worker shift is in flight. */
  runtimeShiftHint?: string | null;
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
  decision: [];
  decisionOption: [option: { id: string; label: string }];
  recoverFailure: [];
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
  if (props.reporting) {
    return (
      props.runtimeShiftHint?.trim() ||
      'Live shift in progress — activity streams below. Open the agent dock for full detail.'
    );
  }
  if (props.liveBusy && props.runtimeShiftHint?.trim()) {
    return props.runtimeShiftHint.trim();
  }
  if (failure.value) {
    return failure.value;
  }
  if (!props.employee.enabled) {
    return 'Paused — continuous shifts are off for this teammate.';
  }
  return employeeTalkLine(props.employee) || `${employeeStatusLabel(employeeDisplayStatus(props.employee))} on ${props.employee.owns || 'assigned work'}.`;
});
const transcriptLines = computed((): TeamPanelTranscriptLine[] => {
  if (!props.reporting || !props.transcript?.trim()) {
    return [];
  }
  return buildTeamPanelTranscriptLines(props.transcript, {
    streaming: true,
    maxLines: 14,
  });
});
const showReceipt = computed(
  () => Boolean(receiptDetail.value || receiptRunId.value) && !props.reporting,
);
const showDeliveryLinks = computed(() => Boolean(deliveryLinks.value) && !props.reporting);
const receiptDetail = computed(() => employeeDockReceiptDetail(props.employee));
const receiptRunId = computed(() => employeeDockReceiptRunId(props.employee));
const receiptRunLabel = computed(() => employeeDockReceiptRunLabel(receiptRunId.value));
const receiptsAction = computed(() =>
  props.actions.find((action) => action.id === 'receipts') ?? null,
);
const displayActions = computed(() =>
  employeeDockDisplayActions(props.actions, props.employee),
);
const dockPrimaryActionIds = new Set(['start_now', 'retry', 'talk', 'stop']);
const dockPrimaryActions = computed(() =>
  displayActions.value.filter((action) => dockPrimaryActionIds.has(action.id)),
);
const dockSecondaryActions = computed(() =>
  displayActions.value.filter((action) => !dockPrimaryActionIds.has(action.id)),
);
const pendingDecision = computed(() => Boolean(props.employee.pending_decision_id));
const pendingDecisionCopy = computed(
  () => resolvePendingDecisionPrompt(props.employee) || 'Review the pending decision',
);
const pendingDecisionSubject = computed(() =>
  failedShiftSubjectFromDecisionTitle(props.employee.pending_decision_title),
);
const pendingDecisionOptions = computed(() =>
  pendingDecisionCardOptions(props.employee).slice(0, 3),
);
const hasSafeRetryDecisionOption = computed(() =>
  pendingDecisionOptions.value.some((option) => option.id === APPROVE_PENDING_RECOVERY_ID),
);
const retryActionLabel = computed(
  () => displayActions.value.find((action) => action.id === 'retry')?.label ?? 'Try again',
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
    <button
      v-if="employee.owns?.trim()"
      type="button"
      class="agent-persona-dock__owns-info"
      :title="employee.owns"
      :aria-label="`${employee.name} scope: ${employee.owns}`"
    >
      <span aria-hidden="true">i</span>
    </button>
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
            v-if="runtimeShiftHint"
            class="company-roster__badge company-roster__badge--runtime"
            :title="runtimeShiftHint"
          >
            Headless
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
      </div>
      <span
        class="agent-persona-dock__status"
        :data-status="employeeDisplayStatus(employee)"
      >
        {{ employeeStatusLabel(employeeDisplayStatus(employee)) }}
      </span>
    </header>

    <div class="agent-persona-dock__scroll">
    <div class="agent-persona-dock__body">
    <button
      v-if="failure"
      type="button"
      class="agent-persona-dock__beat agent-persona-dock__beat-btn"
      :class="{
        'agent-persona-dock__beat--failed': !interruptedShift,
        'agent-persona-dock__beat--interrupted': interruptedShift,
      }"
      :title="beatDetailTooltip ?? undefined"
      :aria-label="`${failureBeatAriaLabel ?? liveBeat}. Tap to ${retryActionLabel}.`"
      @click="emit('recoverFailure')"
    >
      {{ liveBeat }}
      <span class="agent-persona-dock__beat-cta">{{ retryActionLabel }} →</span>
    </button>
    <p
      v-else
      class="agent-persona-dock__beat"
      :class="{ 'agent-persona-dock__beat--live': reporting }"
      :title="beatDetailTooltip ?? undefined"
      role="status"
    >
      {{ liveBeat }}
    </p>

    <section
      v-if="pendingDecision"
      class="agent-persona-dock__decision-alert"
      aria-labelledby="agent-pending-decision-title"
    >
      <button
        type="button"
        class="agent-persona-dock__decision-main"
        :aria-label="`Review ${employee.name}'s pending decision in the agent composer`"
        @click="emit('decision')"
      >
        <span class="agent-persona-dock__decision-icon" aria-hidden="true">!</span>
        <span class="agent-persona-dock__decision-copy">
          <span class="agent-persona-dock__decision-kicker">Decision required</span>
          <strong id="agent-pending-decision-title">{{ pendingDecisionCopy }}</strong>
          <small v-if="pendingDecisionSubject && pendingDecisionSubject.role !== (employee.role ?? '').trim().toLowerCase()">
            {{ employee.name }} is holding this decision for {{ pendingDecisionSubject.name }} ({{ pendingDecisionSubject.role }})
          </small>
          <small v-else-if="pendingDecisionSubject">
            Shift failure · {{ pendingDecisionSubject.name }} ({{ pendingDecisionSubject.role }})
          </small>
          <small v-else-if="pendingDecisionOptions.length">
            {{ pendingDecisionOptions.map((option) => option.label).join(' · ') }}
          </small>
        </span>
        <span class="agent-persona-dock__decision-open">Open decision in composer →</span>
      </button>
      <p class="agent-persona-dock__decision-help">
        Opens this decision as an editable operator reply. Safe retry only approves a narrow
        recovery for this failed shift; it does not deploy or make broad changes.
      </p>
      <div
        v-if="pendingDecisionOptions.length"
        class="agent-persona-dock__decision-options"
        role="group"
        :aria-label="`Decision options for ${employee.name}`"
      >
        <button
          v-for="option in pendingDecisionOptions"
          :key="option.id"
          type="button"
          class="agent-persona-dock__decision-option"
          :class="{
            'agent-persona-dock__decision-option--primary':
              option.id === APPROVE_PENDING_RECOVERY_ID,
          }"
          @click="emit('decisionOption', option)"
        >
          {{ option.label }}
        </button>
      </div>
      <p v-if="hasSafeRetryDecisionOption" class="agent-persona-dock__decision-footnote">
        Use safe retry for recoverable runtime, quota, connectivity, or stale-shift blockers. Use
        composer review when you need to steer the team.
      </p>
    </section>

    <ul
      v-if="transcriptLines.length"
      ref="transcriptRef"
      class="agent-persona-dock__transcript-list"
      aria-label="Live shift activity"
      aria-live="polite"
    >
      <li
        v-for="line in transcriptLines"
        :key="line.id"
        class="agent-persona-dock__transcript-line"
        :data-kind="line.kind"
        :data-live="line.live ? 'true' : undefined"
      >
        {{ line.text }}
      </li>
    </ul>

    <div
      v-if="showDeliveryLinks && deliveryLinks"
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

    <section v-if="showReceipt" class="agent-persona-dock__receipt">
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
    </div>

    <div
      v-if="dockPrimaryActions.length || dockSecondaryActions.length"
      class="agent-persona-dock__action-stack"
      role="group"
      :aria-label="`Actions for ${employee.name}`"
    >
      <div
        v-if="dockPrimaryActions.length"
        class="agent-persona-dock__actions agent-persona-dock__actions--primary"
      >
        <button
          v-for="action in dockPrimaryActions"
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
      <div
        v-if="dockSecondaryActions.length"
        class="agent-persona-dock__actions agent-persona-dock__actions--secondary"
      >
        <button
          v-for="action in dockSecondaryActions"
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
    </div>
    </div>
  </article>
</template>
