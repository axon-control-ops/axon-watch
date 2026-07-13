<script setup lang="ts">
import { computed } from 'vue';

import HudSeamCard from '../HudSeamCard.vue';
import HandoffToIdeButton from './HandoffToIdeButton.vue';
import SentryIssuesList from './SentryIssuesList.vue';
import VerifyDismissSignalButton from './VerifyDismissSignalButton.vue';
import {
  formatRunDisplayName,
  formatRunShortId,
} from '../../lib/run-display';
import { runPhaseProgress, runPhaseTag } from '../../lib/mockup-shell-view';
import {
  deliveryStateLabel,
  deliveryStateTooltip,
  signalOperatorHint,
  watchRuleLabel,
  watchRuleTooltip,
} from '../../lib/operator-signal-hints';
import { useShellStore } from '../../stores/shell';

const props = withDefaults(
  defineProps<{
    variant?: 'sidebar' | 'dock';
    sections?: 'all' | 'run-only';
  }>(),
  {
    variant: 'dock',
    sections: 'all',
  },
);

const shell = useShellStore();

const activeRun = computed(() => shell.primaryActiveRun);

const recentReceipts = computed(() => {
  const limit = props.variant === 'sidebar' ? 2 : 3;
  return shell.runHistoryRows.slice(-limit).reverse();
});

const otherReviewReadyRuns = computed(() =>
  shell.runs.filter(
    (run) =>
      run.phase === 'review_ready' &&
      run.workspace_id === shell.currentWorkspace?.workspace_id &&
      run.run_id !== activeRun.value?.run_id,
  ),
);

const otherReviewReadyRunsShown = computed(() => otherReviewReadyRuns.value.slice(0, 3));
const otherReviewReadyRunsOverflow = computed(() =>
  Math.max(0, otherReviewReadyRuns.value.length - otherReviewReadyRunsShown.value.length),
);

const reviewReadyRunCount = computed(
  () =>
    shell.runs.filter(
      (run) =>
        run.phase === 'review_ready' &&
        run.workspace_id === shell.currentWorkspace?.workspace_id,
    ).length,
);

const showStopAction = computed(
  () =>
    Boolean(activeRun.value?.can_stop) || activeRun.value?.phase === 'executing',
);

const showReviewActions = computed(
  () =>
    Boolean(activeRun.value?.can_resume) ||
    shell.canCompletePrimaryRun,
);

function signalCount(): number {
  return shell.workspaceAttentionSignalCount;
}

const attentionSignals = computed(() => shell.attentionSignals);

function signalSeverityLabel(severity: string | null | undefined): string {
  const normalized = severity ?? 'info';
  return normalized === 'info' ? 'INFO' : normalized.toUpperCase();
}

function phaseTagClass(phase: string | undefined): string {
  if (phase === 'review_ready') {
    return 'dock-tag--review';
  }
  if (phase === 'executing') {
    return 'dock-tag--execute';
  }
  if (phase === 'awaiting_approval') {
    return 'dock-tag--warning';
  }
  return '';
}

function isSignalExpanded(signalId: string): boolean {
  return shell.highlightedSignalId === signalId;
}

function signalHint(signal: {
  signal_id: string;
  title: string;
  summary?: string | null;
  meta?: Record<string, unknown> | null;
}): string {
  return signalOperatorHint({
    signalId: signal.signal_id,
    title: signal.title,
    summary: signal.summary,
    meta: signal.meta,
  });
}
</script>

<template>
  <div
    class="attention-stack"
    :class="{
      'attention-stack--sidebar': variant === 'sidebar',
      'attention-stack--dock': variant === 'dock',
      'attention-stack--run-only': sections === 'run-only',
    }"
  >
    <HudSeamCard
      seam-id="dock-seam-run"
      :title="shell.dockSeamState('run')?.title ?? 'Active Run'"
      seam-class="dock-seam dock-seam--run"
      :show-view-all="variant === 'dock'"
    >
      <div
        v-if="activeRun"
        class="dock-run-seam"
        :class="{ 'dock-run-seam--sidebar': variant === 'sidebar' }"
      >
        <div class="dock-run-seam__header">
          <div class="dock-run-seam__title-block">
            <strong>{{ formatRunDisplayName(activeRun) }}</strong>
            <span class="dock-run-seam__short-id">#{{ formatRunShortId(activeRun.run_id) }}</span>
          </div>
          <span class="dock-tag" :class="phaseTagClass(activeRun.phase)">
            {{ runPhaseTag(activeRun.phase) }}
          </span>
        </div>

        <div class="dock-progress" role="progressbar" :aria-valuenow="runPhaseProgress(activeRun.phase)">
          <div
            class="dock-progress__fill"
            :class="{ 'dock-progress__fill--review': activeRun.phase === 'review_ready' }"
            :style="{ width: `${runPhaseProgress(activeRun.phase)}%` }"
          />
        </div>

        <p
          v-if="activeRun.current_step"
          class="dock-run-seam__step"
          :title="activeRun.current_step"
        >
          {{ activeRun.current_step }}
        </p>

        <ul v-if="recentReceipts.length" class="dock-run-receipts" aria-label="Recent run receipts">
          <li v-for="row in recentReceipts" :key="row.id" class="dock-run-receipts__item">
            <span class="dock-run-receipts__label">{{ row.label }}</span>
          </li>
        </ul>

        <div v-if="otherReviewReadyRuns.length" class="dock-run-seam__also-waiting">
          <div class="dock-run-seam__also-header">
            <span class="dock-run-seam__also-label">
              Also waiting
              <span v-if="reviewReadyRunCount > 1">({{ reviewReadyRunCount }})</span>
            </span>
            <button
              v-if="reviewReadyRunCount > 1"
              type="button"
              class="dock-run-seam__clear-queue"
              :disabled="shell.runMutationPending"
              @click="shell.completeAllReviewReadyRuns()"
            >
              {{ shell.runMutationState === 'completing' ? 'Clearing…' : 'Complete all' }}
            </button>
          </div>
          <ul class="dock-run-seam__also-list">
            <li v-for="run in otherReviewReadyRunsShown" :key="run.run_id">
              {{ formatRunDisplayName(run) }}
            </li>
          </ul>
          <p v-if="otherReviewReadyRunsOverflow > 0" class="dock-run-seam__also-more">
            + {{ otherReviewReadyRunsOverflow }} more — use Complete all
          </p>
        </div>

        <div v-if="showReviewActions || showStopAction" class="run-actions run-actions--sidebar">
          <button
            v-if="activeRun.can_resume && activeRun.phase !== 'review_ready'"
            type="button"
            class="run-actions__button run-actions__button--warning"
            :disabled="!shell.canResumePrimaryRun"
            @click="shell.resumePrimaryRun()"
          >
            {{ shell.runMutationState === 'resuming' ? 'RESUMING…' : 'RESUME' }}
          </button>
          <button
            v-if="shell.canCompletePrimaryRun"
            type="button"
            class="run-actions__button run-actions__button--primary"
            :disabled="shell.runMutationPending"
            @click="shell.completePrimaryRun()"
          >
            {{ shell.runMutationState === 'completing' ? 'COMPLETING…' : 'COMPLETE' }}
          </button>
          <button
            v-if="showStopAction"
            type="button"
            class="run-actions__button run-actions__button--ghost"
            :disabled="!shell.canStopPrimaryRun && activeRun.phase !== 'executing'"
            @click="shell.stopPrimaryRun()"
          >
            {{ shell.runMutationState === 'stopping' ? 'STOPPING…' : 'STOP' }}
          </button>
        </div>
      </div>
      <p v-else class="region-copy dock-run-seam__empty">No active run — send a command from the right dock.</p>
    </HudSeamCard>

    <HudSeamCard
      v-if="sections === 'all'"
      seam-id="dock-seam-approvals"
      :title="shell.dockSeamState('approvals')?.title ?? 'Approvals'"
      seam-class="dock-seam dock-seam--approvals"
      :alert="shell.pendingApprovalsCount > 0"
      :collapsed="variant === 'dock' ? (shell.dockSeamState('approvals')?.collapsed ?? false) : false"
      :compact-summary="shell.approvalsSummaryLabel"
      :collapsible="variant === 'dock' && shell.layoutMode === 'ide'"
      :show-view-all="variant === 'dock'"
      @toggle="shell.toggleDockSeam('approvals')"
    >
      <p class="dock-seam__lead">
        {{ shell.pendingApprovalsCount }} approval{{ shell.pendingApprovalsCount === 1 ? '' : 's' }}
        pending
      </p>
      <ul v-if="shell.operatorBriefing?.pending_approvals.items.length" class="dock-list">
        <li
          v-for="(item, index) in shell.operatorBriefing.pending_approvals.items"
          :key="item.approval_id"
          class="dock-list__item"
        >
          <span class="dock-list__title">{{ item.approval_id }}</span>
          <span class="dock-tag dock-tag--high">{{ index === 0 ? 'HIGH' : 'MEDIUM' }}</span>
        </li>
      </ul>
      <p v-else class="region-copy">No pending approvals</p>

      <div v-if="shell.primaryApprovalRun" class="dock-approval-run">
        <p class="dock-approval-run__label">Primary approval run</p>
        <div class="dock-approval-run__header">
          <strong>{{ formatRunDisplayName(shell.primaryApprovalRun) }}</strong>
          <span class="dock-tag dock-tag--warning">AWAITING</span>
        </div>
        <p class="region-copy">{{ shell.primaryApprovalRun.summary }}</p>
      </div>

      <p v-if="shell.runMutationError" class="dock-seam__error" role="alert">
        {{ shell.runMutationError }}
      </p>

      <div v-if="shell.pendingApprovalsCount > 0" class="run-actions run-actions--approval">
        <button
          type="button"
          class="run-actions__button run-actions__button--primary"
          :disabled="!shell.canApprovePrimaryRun"
          @click="shell.approvePrimaryRun()"
        >
          {{ shell.runMutationState === 'approving' ? 'APPROVING…' : 'APPROVE RUN' }}
        </button>
        <button
          type="button"
          class="run-actions__button run-actions__button--danger"
          :disabled="!shell.canRejectPrimaryRun"
          @click="shell.rejectPrimaryRun()"
        >
          {{ shell.runMutationState === 'rejecting' ? 'REJECTING…' : 'REJECT RUN' }}
        </button>
      </div>
    </HudSeamCard>

    <HudSeamCard
      v-if="sections === 'all'"
      seam-id="dock-seam-signals"
      :title="shell.dockSeamState('signals')?.title ?? 'Signals'"
      seam-class="dock-seam dock-seam--signals"
      :emphasized="shell.signalsSeamEmphasized"
      :show-view-all="variant === 'dock'"
    >
      <div class="dock-signals__header">
        <p class="dock-seam__lead dock-seam__lead--neutral">
          {{ signalCount() }} active signal{{ signalCount() === 1 ? '' : 's' }}
        </p>
        <button
          v-if="signalCount() > 0"
          type="button"
          class="dock-signals__clear"
          :disabled="shell.signalClearState === 'clearing'"
          @click="shell.clearActiveSignals()"
        >
          {{ shell.signalClearState === 'clearing' ? 'CLEARING…' : 'CLEAR' }}
        </button>
      </div>
      <p class="dock-signals__hint">
        Tap title for details · OBSERVE / DELIVERED = status labels
      </p>
      <ul v-if="attentionSignals.length" class="dock-list dock-list--signals">
        <li
          v-for="signal in attentionSignals"
          :key="signal.signal_id"
          class="dock-list__item dock-signal-row"
          :class="{ 'dock-signal-row--expanded': isSignalExpanded(signal.signal_id) }"
        >
          <div class="dock-signal-row__main">
            <button
              type="button"
              class="dock-signal-row__toggle"
              :aria-expanded="isSignalExpanded(signal.signal_id)"
              @click="shell.toggleSignalDetails(signal.signal_id)"
            >
              <span class="dock-list__title">{{ signal.title }}</span>
              <span class="dock-signal-row__toggle-label">
                {{ isSignalExpanded(signal.signal_id) ? 'Hide' : 'Details' }}
              </span>
            </button>
            <div class="dock-signal-row__meta" aria-label="Signal status labels">
              <span
                class="dock-tag dock-tag--status"
                :class="{
                  'dock-tag--high': signal.severity === 'high' || signal.severity === 'critical',
                  'dock-tag--warning': signal.severity === 'warning',
                  'dock-tag--info': signal.severity === 'info',
                }"
                :title="`${signal.severity ?? 'info'} severity (read-only)`"
              >
                {{ signalSeverityLabel(signal.severity) }}
              </span>
              <span
                v-if="signal.watch_rule?.mode"
                class="dock-tag dock-tag--status dock-tag--kairo"
                :title="watchRuleTooltip(signal.watch_rule.mode)"
              >
                {{ watchRuleLabel(signal.watch_rule.mode).toUpperCase() }}
              </span>
              <span
                v-if="deliveryStateLabel(signal.delivery_state ?? undefined)"
                class="dock-tag dock-tag--status dock-tag--delivery"
                :title="deliveryStateTooltip(signal.delivery_state ?? undefined)"
              >
                {{ deliveryStateLabel(signal.delivery_state ?? undefined)?.toUpperCase() }}
              </span>
            </div>
          </div>
          <div
            v-if="isSignalExpanded(signal.signal_id)"
            class="dock-signal-row__detail"
            role="region"
            :aria-label="`Details for ${signal.title}`"
          >
            <p class="dock-signal-row__detail-copy">{{ signalHint(signal) }}</p>
            <p v-if="signal.summary && signal.summary !== signalHint(signal)" class="region-copy">
              {{ signal.summary }}
            </p>
            <p v-if="signal.latest_receipt_id" class="region-copy dock-signal-row__receipt">
              Receipt {{ signal.latest_receipt_id }}
            </p>
            <SentryIssuesList
              :meta="signal.meta"
              compact
            />
            <HandoffToIdeButton
              :signal-id="signal.signal_id"
              :workspace-id="signal.workspace_id"
              :title="signal.title"
              :summary="signal.summary"
              :meta="signal.meta"
              compact
            />
            <VerifyDismissSignalButton
              :signal-id="signal.signal_id"
              compact
            />
          </div>
        </li>
      </ul>
      <p v-else class="region-copy">{{ shell.inboxStateLabel }}</p>
      <p v-if="shell.signalClearError" class="dock-seam__error" role="alert">
        {{ shell.signalClearError }}
      </p>
    </HudSeamCard>
  </div>
</template>
