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
} from '../../lib/ide-interrupt-panel-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const showPanel = computed(
  () => shell.layoutMode === 'ide' && shell.idePresenceProfile === 'interrupt',
);

const topSignal = computed(() => shell.operatorBriefing?.top_signals[0] ?? null);

const headline = computed(() =>
  resolveIdeInterruptHeadline({
    pendingApprovalsCount: shell.pendingApprovalsCount,
    topSignal: topSignal.value,
    watchConnected: Boolean(shell.runtimeSummary?.watch.connected),
    degradedActive: Boolean(shell.runtimeSummary?.degraded.active),
    primaryRunPhase: shell.primaryActiveRun?.phase,
  }),
);

const detailLine = computed(() =>
  resolveIdeInterruptDetailLine({
    pendingApprovalsCount: shell.pendingApprovalsCount,
    topSignal: topSignal.value,
    watchConnected: Boolean(shell.runtimeSummary?.watch.connected),
    degradedActive: Boolean(shell.runtimeSummary?.degraded.active),
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
    degradedActive: Boolean(shell.runtimeSummary?.degraded.active),
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
  () => shell.canResumeIdeAgentRun || Boolean(shell.primaryActiveRun?.can_resume),
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
        {{ shell.runMutationState === 'resuming' ? '…' : 'Resume' }}
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
.ide-interrupt-topbar {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 0;
  max-width: 100%;
  height: calc(var(--topbar-height) - 0.42rem);
  padding: 0 0.55rem;
  border: 1px solid rgba(255, 120, 72, 0.38);
  border-radius: 0.35rem;
  background: rgba(24, 12, 8, 0.88);
  box-shadow: inset 0 0 0 1px rgba(255, 120, 72, 0.08);
}

.ide-interrupt-topbar__badge {
  flex-shrink: 0;
  font-size: 0.56rem;
  letter-spacing: 0.08em;
  font-weight: 700;
  color: rgba(255, 160, 120, 0.95);
}

.ide-interrupt-topbar__summary {
  margin: 0;
  min-width: 0;
  flex: 1 1 auto;
  font-size: 0.68rem;
  line-height: 1.2;
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

.ide-interrupt-topbar__button {
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 0.3rem;
  background: rgba(255, 255, 255, 0.04);
  color: inherit;
  cursor: pointer;
  font: inherit;
  font-size: 0.58rem;
  letter-spacing: 0.04em;
  line-height: 1;
  padding: 0.22rem 0.42rem;
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
