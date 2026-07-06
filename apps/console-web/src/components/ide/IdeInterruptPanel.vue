<script setup lang="ts">
import { computed } from 'vue';

import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const showPanel = computed(
  () => shell.layoutMode === 'ide' && shell.idePresenceProfile === 'interrupt',
);

const headline = computed(() => {
  if (shell.pendingApprovalsCount > 0) {
    const count = shell.pendingApprovalsCount;
    return `${count} approval${count === 1 ? '' : 's'} waiting for your review`;
  }

  const topSignal = shell.operatorBriefing?.top_signals[0];
  if (topSignal?.title) {
    return topSignal.title;
  }

  if (shell.runtimeSummary && !shell.runtimeSummary.watch.connected) {
    return 'Watch connector offline';
  }

  if (shell.runtimeSummary?.degraded.active) {
    return 'Runtime degraded — attention required';
  }

  if (shell.primaryActiveRun?.phase === 'awaiting_approval') {
    return 'Run blocked — awaiting approval';
  }

  return 'Attention required';
});

const detailLine = computed(() => {
  if (shell.pendingApprovalsCount > 0) {
    return 'Review before the agent can continue.';
  }

  const topSignal = shell.operatorBriefing?.top_signals[0];
  if (topSignal?.summary) {
    return topSignal.summary;
  }

  if (shell.primaryActiveRun?.current_step) {
    return shell.primaryActiveRun.current_step;
  }

  return 'Open Attention to review signals, approvals, or run state.';
});

const showApprovalAction = computed(() => shell.pendingApprovalsCount > 0);

const showAttentionAction = computed(
  () =>
    shell.pendingApprovalsCount > 0 ||
    (shell.operatorBriefing?.top_signals.length ?? 0) > 0 ||
    Boolean(shell.runtimeSummary?.degraded.active),
);

const showStopAction = computed(
  () =>
    Boolean(shell.primaryActiveRun?.can_stop) ||
    shell.primaryActiveRun?.phase === 'executing',
);

const showResumeAction = computed(() => Boolean(shell.primaryActiveRun?.can_resume));
</script>

<template>
  <section
    v-if="showPanel"
    class="ide-interrupt-panel hud-panel-frame"
    aria-label="IDE attention required"
  >
    <div class="ide-interrupt-panel__copy">
      <p class="ide-interrupt-panel__eyebrow">Attention required</p>
      <p class="ide-interrupt-panel__headline">{{ headline }}</p>
      <p class="ide-interrupt-panel__detail">{{ detailLine }}</p>
    </div>
    <div class="ide-interrupt-panel__actions">
      <button
        v-if="showApprovalAction"
        type="button"
        class="ide-interrupt-panel__button ide-interrupt-panel__button--primary"
        @click="shell.focusAttentionSidebar()"
      >
        Review approvals
      </button>
      <button
        v-if="showAttentionAction"
        type="button"
        class="ide-interrupt-panel__button"
        @click="shell.focusAttentionSidebar(shell.operatorBriefing?.top_signals[0]?.signal_id)"
      >
        Open Attention
      </button>
      <button
        v-if="showResumeAction"
        type="button"
        class="ide-interrupt-panel__button ide-interrupt-panel__button--warning"
        :disabled="!shell.canResumePrimaryRun"
        @click="shell.resumePrimaryRun()"
      >
        {{ shell.runMutationState === 'resuming' ? 'Resuming…' : 'Resume run' }}
      </button>
      <button
        v-if="showStopAction"
        type="button"
        class="ide-interrupt-panel__button ide-interrupt-panel__button--ghost"
        :disabled="!shell.canStopPrimaryRun && shell.primaryActiveRun?.phase !== 'executing'"
        @click="shell.stopPrimaryRun()"
      >
        {{ shell.runMutationState === 'stopping' ? 'Stopping…' : 'Stop run' }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.ide-interrupt-panel {
  position: fixed;
  top: calc(var(--topbar-height) + var(--shell-gutter));
  left: var(--shell-gutter);
  right: var(--shell-gutter);
  z-index: 25;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.65rem 0.85rem;
  border: 1px solid rgba(255, 120, 72, 0.35);
  border-radius: 0.5rem;
  background: rgba(18, 12, 10, 0.94);
  box-shadow: 0 0.35rem 1.25rem rgba(0, 0, 0, 0.35);
}

.ide-interrupt-panel__copy {
  min-width: 0;
}

.ide-interrupt-panel__eyebrow {
  margin: 0;
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(255, 160, 120, 0.88);
}

.ide-interrupt-panel__headline {
  margin: 0.15rem 0 0;
  font-size: 0.92rem;
  font-weight: 600;
}

.ide-interrupt-panel__detail {
  margin: 0.2rem 0 0;
  font-size: 0.78rem;
  opacity: 0.78;
}

.ide-interrupt-panel__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.45rem;
  flex-shrink: 0;
}

.ide-interrupt-panel__button {
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 0.35rem;
  background: rgba(255, 255, 255, 0.04);
  color: inherit;
  cursor: pointer;
  font: inherit;
  font-size: 0.78rem;
  padding: 0.35rem 0.65rem;
}

.ide-interrupt-panel__button--primary {
  border-color: rgba(255, 120, 72, 0.45);
  background: rgba(255, 120, 72, 0.14);
}

.ide-interrupt-panel__button--warning {
  border-color: rgba(255, 196, 72, 0.45);
  background: rgba(255, 196, 72, 0.12);
}

.ide-interrupt-panel__button--ghost {
  opacity: 0.82;
}

.ide-interrupt-panel__button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
