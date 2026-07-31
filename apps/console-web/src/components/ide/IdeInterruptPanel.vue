<script setup lang="ts">
import { computed } from 'vue';

import {
  isIdeInterruptStopDisabled,
  resolveIdeInterruptCompactLabel,
  resolveIdeInterruptDetailLine,
  resolveIdeInterruptHeadline,
  resolveIdeInterruptStopTarget,
  resolveIdeInterruptTooltip,
  shouldShowIdeInterruptAttentionAction,
  shouldShowIdeInterruptStop,
  shouldShowIdeInterruptStrip,
} from '../../lib/ide-interrupt-panel-view';
import {
  localRuntimeDegradedActive,
  remoteIngressAttentionActive,
} from '../../lib/runtime-degraded-scope';
import { runContinueActionLabel } from '../../lib/run-lifecycle-ui';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const showPanel = computed(
  () =>
    shell.layoutMode === 'ide' &&
    shouldShowIdeInterruptStrip({
      presenceProfile: shell.idePresenceProfile,
      pendingApprovalsCount: shell.pendingApprovalsCount,
    }),
);

const topSignal = computed(() => shell.operatorBriefing?.top_signals[0] ?? null);

const headline = computed(() =>
  resolveIdeInterruptHeadline({
    pendingApprovalsCount: shell.pendingApprovalsCount,
    topSignal: topSignal.value,
    watchConnected: Boolean(shell.runtimeSummary?.watch.connected),
    degradedActive: localRuntimeDegradedActive(shell.runtimeSummary?.degraded),
    remoteIngressAttention: remoteIngressAttentionActive(shell.runtimeSummary?.degraded),
    primaryRunPhase: shell.primaryActiveRun?.phase,
  }),
);

const detailLine = computed(() =>
  resolveIdeInterruptDetailLine({
    pendingApprovalsCount: shell.pendingApprovalsCount,
    topSignal: topSignal.value,
    watchConnected: Boolean(shell.runtimeSummary?.watch.connected),
    degradedActive: localRuntimeDegradedActive(shell.runtimeSummary?.degraded),
    remoteIngressAttention: remoteIngressAttentionActive(shell.runtimeSummary?.degraded),
    primaryRunCurrentStep: shell.primaryActiveRun?.current_step,
  }),
);

const compactLabel = computed(() =>
  resolveIdeInterruptCompactLabel(headline.value, detailLine.value),
);

const tooltip = computed(() => resolveIdeInterruptTooltip(headline.value, detailLine.value));

const showApprovalAction = computed(() => shell.pendingApprovalsCount > 0);

const showAttentionAction = computed(() =>
  shouldShowIdeInterruptAttentionAction({
    pendingApprovalsCount: shell.pendingApprovalsCount,
    topSignals: shell.operatorBriefing?.top_signals ?? [],
    degradedActive: localRuntimeDegradedActive(shell.runtimeSummary?.degraded),
  }),
);

const showStopAction = computed(() =>
  shouldShowIdeInterruptStop({
    canStopIdeAgentRun: shell.canStopIdeAgentRun,
    canStopPrimaryRun: shell.canStopPrimaryRun,
    primaryRunPhase: shell.primaryActiveRun?.phase,
    agentStreamActive: shell.agentStreamActive,
  }),
);

const stopDisabled = computed(() =>
  isIdeInterruptStopDisabled({
    runMutationStopping: shell.runMutationState === 'stopping',
    canStopIdeAgentRun: shell.canStopIdeAgentRun,
    canStopPrimaryRun: shell.canStopPrimaryRun,
    primaryRunPhase: shell.primaryActiveRun?.phase,
  }),
);

const showResumeAction = computed(
  () => shell.canResumeIdeAgentRun || shell.canResumePrimaryRun,
);

const resumeActionLabel = computed(() =>
  runContinueActionLabel({
    phase: shell.ideAgentLinkedRun?.phase ?? shell.primaryActiveRun?.phase,
    agentStreamActive: shell.agentStreamActive,
    mode: shell.ideAgentLinkedRun?.mode ?? shell.primaryActiveRun?.mode,
    pending: shell.runMutationState === 'resuming',
    continueLabel: 'Continue',
    resumeLabel: 'Resume',
    pendingLabel: 'Resuming…',
  }),
);

function resumeActiveRun(): void {
  if (shell.canResumeIdeAgentRun) {
    void shell.resumeIdeAgentRun();
    return;
  }

  void shell.resumePrimaryRun();
}

function stopActiveRun(): void {
  if (
    resolveIdeInterruptStopTarget({
      canStopIdeAgentRun: shell.canStopIdeAgentRun,
      agentStreamActive: shell.agentStreamActive,
    }) === 'ide-agent'
  ) {
    void shell.stopIdeAgentRun();
    return;
  }

  void shell.stopPrimaryRun();
}
</script>

<template>
  <div
    v-if="showPanel"
    class="ide-interrupt-topbar"
    role="status"
    aria-live="polite"
    aria-label="IDE attention required"
  >
    <span class="ide-interrupt-topbar__badge">ATTN</span>
    <p class="ide-interrupt-topbar__summary" :title="tooltip">{{ compactLabel }}</p>
    <div class="ide-interrupt-topbar__actions">
      <button
        v-if="showApprovalAction"
        type="button"
        class="ide-interrupt-topbar__button ide-interrupt-topbar__button--primary"
        @click="shell.focusAttentionSidebar()"
      >
        Approvals
      </button>
      <button
        v-if="showAttentionAction"
        type="button"
        class="ide-interrupt-topbar__button"
        @click="shell.focusAttentionSidebar(shell.operatorBriefing?.top_signals[0]?.signal_id)"
      >
        Attention
      </button>
      <button
        v-if="showResumeAction"
        type="button"
        class="ide-interrupt-topbar__button ide-interrupt-topbar__button--warning"
        :disabled="shell.runMutationState === 'resuming' || !(shell.canResumeIdeAgentRun || shell.canResumePrimaryRun)"
        @click="resumeActiveRun()"
      >
        {{ resumeActionLabel }}
      </button>
      <button
        v-if="showStopAction"
        type="button"
        class="ide-interrupt-topbar__button ide-interrupt-topbar__button--ghost"
        :disabled="stopDisabled"
        @click="stopActiveRun()"
      >
        {{ shell.runMutationState === 'stopping' ? '…' : 'Stop' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
/* Height follows the topbar's compact-chip convention (.kairo-presence-module--chip)
   so the strip reads as a sibling of the ATTENTION pill rather than a hairline.
   min-height (not height/max-height) keeps text from being clipped when it is
   resized up to 200% — WCAG 2.2 SC 1.4.4, failure F69. */
.ide-interrupt-topbar {
  display: flex;
  /* .topbar-mockup__runtime-strip defaults to wrap for the operator chip row;
     the strip is a single line so the badge, headline, and controls stay aligned. */
  flex-wrap: nowrap;
  align-items: center;
  gap: 0.35rem;
  min-width: min(100%, 13rem);
  max-width: min(48vw, 34rem);
  min-height: 2.2rem;
  padding: 0.2rem 0.5rem;
  border: 1px solid rgba(255, 120, 72, 0.32);
  border-radius: 0.28rem;
  background: rgba(24, 12, 8, 0.82);
  box-shadow: none;
}

.ide-interrupt-topbar__badge {
  flex-shrink: 0;
  font-size: 0.58rem;
  letter-spacing: 0.06em;
  font-weight: 700;
  color: rgba(255, 160, 120, 0.95);
}

.ide-interrupt-topbar__summary {
  margin: 0;
  min-width: 0;
  flex: 1 1 auto;
  font-size: 0.72rem;
  line-height: 1.25;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ide-interrupt-topbar__actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex-shrink: 0;
}

/* 24px floor keeps these pointer targets at the WCAG 2.2 SC 2.5.8 minimum. */
.ide-interrupt-topbar__button {
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 0.22rem;
  background: rgba(255, 255, 255, 0.04);
  color: inherit;
  cursor: pointer;
  font: inherit;
  font-size: 0.64rem;
  letter-spacing: 0.03em;
  line-height: 1;
  min-height: 24px;
  padding: 0.25rem 0.5rem;
  white-space: nowrap;
}

.ide-interrupt-topbar__button--primary {
  border-color: rgba(255, 120, 72, 0.45);
  background: rgba(255, 120, 72, 0.14);
}

.ide-interrupt-topbar__button--warning {
  border-color: rgba(255, 196, 72, 0.45);
  background: rgba(255, 196, 72, 0.12);
}

.ide-interrupt-topbar__button--ghost {
  opacity: 0.86;
}

.ide-interrupt-topbar__button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
