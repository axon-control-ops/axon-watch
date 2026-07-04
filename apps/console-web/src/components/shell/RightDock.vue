<script setup lang="ts">
import ConversationSeamPanel from '../ConversationSeamPanel.vue';
import DockHeroPanel from '../DockHeroPanel.vue';
import HudSeamCard from '../HudSeamCard.vue';
import { runPhaseProgress, runPhaseTag } from '../../lib/mockup-shell-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

function signalCount(): number {
  return shell.operatorBriefing?.top_signals.length ?? shell.runtimeSummary?.signals.open_count ?? 0;
}
</script>

<template>
  <aside class="region region-right-dock dock-stack dock-stack--mockup">
    <div class="dock-stack__upper">
      <HudSeamCard
        seam-id="dock-seam-run"
        :title="shell.dockSeamState('run')?.title ?? 'Active Run'"
        seam-class="dock-seam dock-seam--run"
        :show-view-all="true"
      >
        <div v-if="shell.primaryActiveRun" class="dock-run-seam">
          <div class="dock-run-seam__header">
            <strong>{{ shell.primaryActiveRun.run_id }}</strong>
            <span class="dock-tag">{{ runPhaseTag(shell.primaryActiveRun.phase) }}</span>
          </div>
          <div class="dock-progress">
            <div
              class="dock-progress__fill"
              :style="{ width: `${runPhaseProgress(shell.primaryActiveRun.phase)}%` }"
            />
          </div>
          <p class="region-copy">{{ shell.primaryActiveRun.summary }}</p>
          <div class="run-actions">
            <button
              v-if="shell.primaryActiveRun.can_stop || shell.primaryActiveRun.phase === 'executing'"
              type="button"
              class="run-actions__button run-actions__button--primary"
              :disabled="!shell.canStopPrimaryRun && shell.primaryActiveRun.phase !== 'executing'"
              @click="shell.stopPrimaryRun()"
            >
              {{ shell.runMutationState === 'stopping' ? 'STOPPING…' : 'STOP RUN' }}
            </button>
          </div>
        </div>
        <p v-else class="region-copy">No active run</p>
      </HudSeamCard>

      <HudSeamCard
        seam-id="dock-seam-approvals"
        :title="shell.dockSeamState('approvals')?.title ?? 'Approvals'"
        seam-class="dock-seam dock-seam--approvals"
        :alert="shell.pendingApprovalsCount > 0"
        :collapsed="shell.dockSeamState('approvals')?.collapsed ?? false"
        :compact-summary="shell.approvalsSummaryLabel"
        :collapsible="shell.layoutMode === 'operator'"
        :show-view-all="true"
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
        <button
          v-if="shell.pendingApprovalsCount > 0"
          type="button"
          class="run-actions__button run-actions__button--warning"
          @click="shell.approvePrimaryRun()"
        >
          REVIEW APPROVALS
        </button>
      </HudSeamCard>

      <HudSeamCard
        seam-id="dock-seam-signals"
        :title="shell.dockSeamState('signals')?.title ?? 'Signals'"
        seam-class="dock-seam dock-seam--signals"
        :show-view-all="true"
      >
        <p class="dock-seam__lead dock-seam__lead--neutral">
          {{ signalCount() }} active signal{{ signalCount() === 1 ? '' : 's' }}
        </p>
        <ul v-if="shell.operatorBriefing?.top_signals.length" class="dock-list">
          <li
            v-for="signal in shell.operatorBriefing.top_signals.slice(0, 3)"
            :key="signal.signal_id"
            class="dock-list__item"
          >
            <span class="dock-list__title">{{ signal.title }}</span>
            <span
              class="dock-tag"
              :class="{
                'dock-tag--high': signal.severity === 'high' || signal.severity === 'critical',
                'dock-tag--warning': signal.severity === 'warning',
                'dock-tag--info': signal.severity === 'info',
              }"
            >
              {{ signal.severity === 'info' ? 'INFO' : signal.severity.toUpperCase() }}
            </span>
          </li>
        </ul>
        <p v-else class="region-copy">{{ shell.inboxStateLabel }}</p>
      </HudSeamCard>

      <HudSeamCard
        seam-id="dock-seam-thread"
        :title="shell.dockSeamState('thread')?.title ?? 'Conversation'"
        seam-class="dock-seam dock-seam--thread"
        :collapsed="shell.dockSeamState('thread')?.collapsed ?? false"
        :compact-summary="shell.dockSeamState('thread')?.compactSummary"
        :collapsible="shell.layoutMode === 'operator'"
        @toggle="shell.toggleDockSeam('thread')"
      >
        <ConversationSeamPanel />
      </HudSeamCard>
    </div>

    <DockHeroPanel />
  </aside>
</template>
