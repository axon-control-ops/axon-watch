<script setup lang="ts">
import { ref } from 'vue';

import BootWakeOverlay from './components/BootWakeOverlay.vue';
import BriefingPanel from './components/BriefingPanel.vue';
import EditorHost from './components/EditorHost.vue';
import HudSeamCard from './components/HudSeamCard.vue';
import KairoChip from './components/KairoChip.vue';
import TerminalHost from './components/TerminalHost.vue';
import WorkspaceFileTree from './components/WorkspaceFileTree.vue';
import { useShellStore } from './stores/shell';

const shell = useShellStore();

const bootComplete = ref(
  typeof window !== 'undefined' &&
    (window.matchMedia('(prefers-reduced-motion: reduce)').matches ||
      sessionStorage.getItem('axon-x-boot-complete') === '1'),
);

const workbenchContractLabels = ['WorkspaceRecord', 'RunRecord'];
const dockContractLabels = [
  'OperatorBriefing',
  'RunRecord',
  'ApprovalRecord',
  'InboxItem',
  'SignalView',
  'ThreadMessage',
];

function completeBoot(): void {
  sessionStorage.setItem('axon-x-boot-complete', '1');
  bootComplete.value = true;
}
</script>

<template>
  <BootWakeOverlay v-if="!bootComplete" @complete="completeBoot" />

  <div
    v-show="bootComplete"
    class="console-shell"
    :data-layout-mode="shell.layoutMode"
  >
    <header class="region region-topbar">
      <div class="topbar-main">
        <div class="topbar-brand">
          <p class="eyebrow">AXON-X</p>
          <h1>Operator console</h1>
        </div>

        <div class="topbar-trail">
          <span class="topbar-trail__label">{{ shell.workspaceStateLabel }}</span>
        </div>

        <div class="chip-row topbar-chips">
          <span class="chip chip--runtime">{{ shell.runtimeStateLabel }}</span>
          <span v-if="shell.primaryActiveRun" class="chip chip--run">{{ shell.runStateLabel }}</span>
        </div>

        <KairoChip :state="shell.kairoPresenceState" />

        <div class="layout-toggle" role="group" aria-label="Layout mode">
          <button
            type="button"
            class="layout-toggle__button"
            :class="{ 'layout-toggle__button--active': shell.layoutMode === 'operator' }"
            :aria-pressed="shell.layoutMode === 'operator'"
            @click="shell.setLayoutMode('operator')"
          >
            Operator
          </button>
          <button
            type="button"
            class="layout-toggle__button"
            :class="{ 'layout-toggle__button--active': shell.layoutMode === 'ide' }"
            :aria-pressed="shell.layoutMode === 'ide'"
            @click="shell.setLayoutMode('ide')"
          >
            IDE
          </button>
        </div>
      </div>

      <p v-if="shell.showDevSeams" class="smoke-banner dev-scaffold">
        Smoke test: open a nested file in the <strong>explorer</strong> → edit →
        <strong>Save</strong> → run <code>pwd</code> / <code>echo hello</code> in the terminal below.
      </p>
    </header>

    <aside class="region region-left-sidebar">
      <div v-if="shell.showDevSeams" class="region-header dev-scaffold">
        <div>
          <p class="eyebrow">Left Sidebar</p>
          <h2>Workspace and explorer seam</h2>
        </div>
      </div>

      <HudSeamCard title="Workspace">
        <strong>{{ shell.workspaceStateLabel }}</strong>
        <p class="region-copy">
          {{ shell.workspaces.length }} workspace{{ shell.workspaces.length === 1 ? '' : 's' }} loaded
        </p>

        <div class="workspace-list">
          <button
            v-for="workspace in shell.workspaces"
            :key="workspace.workspace_id"
            type="button"
            class="workspace-list__button"
            :class="{ 'workspace-list__button--active': shell.currentWorkspace?.workspace_id === workspace.workspace_id }"
            @click="shell.setCurrentWorkspace(workspace.workspace_id)"
          >
            {{ workspace.workspace_id }}
          </button>
        </div>
        <p v-if="shell.workspacesError" class="region-copy">{{ shell.workspacesError }}</p>
      </HudSeamCard>

      <HudSeamCard title="Explorer">
        <WorkspaceFileTree
          :entries="shell.workspaceFileEntries"
          :active-path="shell.activeWorkspaceFilePath"
          :load-state="shell.workspaceFilesLoadState"
          :error="shell.workspaceFilesError"
          @open="shell.openWorkspaceFile"
        />
      </HudSeamCard>
    </aside>

    <main class="region region-center-workbench">
      <div v-if="shell.showDevSeams" class="region-header dev-scaffold">
        <div>
          <p class="eyebrow">Center Workbench</p>
          <h2>Editor and preview host</h2>
        </div>
      </div>

      <div class="tab-strip">
        <button
          v-for="tab in shell.editorTabs"
          :key="tab.id"
          type="button"
          class="tab-strip__tab"
          :class="{ 'tab-strip__tab--active': shell.activeEditorTabId === tab.id }"
          @click="shell.setActiveEditorTab(tab.id)"
        >
          {{ tab.title }}
        </button>
      </div>

      <div v-if="shell.activeEditorTabId === 'editor-shell'" class="tab-strip tab-strip--documents">
        <button
          v-for="document in shell.editorDocuments"
          :key="document.id"
          type="button"
          class="tab-strip__tab"
          :class="{
            'tab-strip__tab--active': shell.activeEditorDocumentId === document.id,
            'tab-strip__tab--file': document.source === 'file',
          }"
          @click="shell.setActiveEditorDocument(document.id)"
        >
          {{ document.title }}
        </button>
      </div>

      <div class="workbench-panels workbench-panels--single">
        <section
          v-if="shell.activeEditorTabId === 'editor-shell'"
          class="workbench-surface workbench-surface--host"
        >
          <EditorHost
            v-if="shell.activeEditorDocument"
            :title="shell.activeEditorDocument.title"
            :value="shell.activeEditorDocument.value"
            :language="shell.activeEditorDocument.language"
            :description="shell.activeEditorDocument.description"
            :read-only="shell.activeEditorDocument.readOnly"
            :dirty="shell.activeEditorDocument.dirty"
            @value-change="shell.updateActiveFileContent"
            @save="shell.saveActiveFileDocument"
          />
          <p v-if="shell.fileSaveError" class="region-copy">{{ shell.fileSaveError }}</p>
          <p v-if="shell.workspaceFilesError" class="region-copy">{{ shell.workspaceFilesError }}</p>
        </section>

        <section v-else class="workbench-surface">
          <p class="workbench-surface__label">Preview</p>
          <strong>Browser / diff host</strong>
          <p class="region-copy">Preview surfaces share the same shell truth in both layout modes.</p>
        </section>
      </div>

      <div v-if="shell.showDevSeams" class="contract-row contract-row--dev">
        <span v-for="label in workbenchContractLabels" :key="label" class="contract-pill">
          {{ label }}
        </span>
      </div>
    </main>

    <section class="region region-bottom-panel">
      <div v-if="shell.showDevSeams" class="region-header dev-scaffold">
        <div>
          <p class="eyebrow">Bottom Panel</p>
          <h2>Terminal and runtime strip host</h2>
        </div>
      </div>

      <div class="bottom-panel-grid">
        <HudSeamCard title="Terminal" class="bottom-panel-terminal">
          <TerminalHost
            :workspace-id="shell.currentWorkspace?.workspace_id ?? null"
            :run-summary="shell.primaryActiveRun ? `${shell.primaryActiveRun.run_id} · ${shell.primaryActiveRun.phase} · ${shell.primaryActiveRun.status}` : null"
            :primary-signal-id="shell.workspacePrimarySignal?.signal_id ?? null"
            :runtime-connected="Boolean(shell.runtimeSummary?.watch.connected)"
          />
        </HudSeamCard>

        <HudSeamCard v-if="shell.runtimeSummary" title="Runtime">
          <strong>
            {{ shell.runtimeSummary.runtime_identity.provider_name }} /
            {{ shell.runtimeSummary.runtime_identity.model_name }}
          </strong>
          <p class="region-copy">
            {{ shell.runtimeSummary.active_runs.length }} active run(s),
            {{ shell.runtimeSummary.signals.open_count }} open signal(s).
          </p>
        </HudSeamCard>

        <HudSeamCard v-else-if="shell.runtimeSummaryLoadState === 'error'" title="Runtime">
          <strong>Unavailable</strong>
          <p class="region-copy">{{ shell.runtimeSummaryError }}</p>
        </HudSeamCard>
      </div>
    </section>

    <aside class="region region-right-dock dock-stack">
      <div v-if="shell.showDevSeams" class="region-header dev-scaffold">
        <div>
          <p class="eyebrow">Right Dock</p>
          <h2>Agent dock and signal summary host</h2>
        </div>
      </div>

      <HudSeamCard
        title="KAIRO Briefing"
        seam-class="dock-seam dock-seam--briefing"
        :hero="shell.layoutMode === 'operator'"
      >
        <BriefingPanel
          :briefing="shell.operatorBriefing"
          :load-state="shell.briefingLoadState"
          :error="shell.briefingError"
          :hero="shell.layoutMode === 'operator'"
        />
      </HudSeamCard>

      <HudSeamCard title="Approvals" seam-class="dock-seam dock-seam--approvals">
        <strong v-if="shell.primaryApprovalRun">
          {{ shell.primaryApprovalRun.run_id }} · {{ shell.primaryApprovalRun.phase }}
        </strong>
        <p v-else class="region-copy">No pending approvals</p>
        <div
          v-if="shell.primaryApprovalRun?.can_approve || shell.primaryApprovalRun?.phase === 'awaiting_approval'"
          class="run-actions"
        >
          <button
            v-if="shell.primaryApprovalRun?.can_approve"
            type="button"
            class="run-actions__button"
            :disabled="!shell.canApprovePrimaryRun"
            @click="shell.approvePrimaryRun()"
          >
            {{ shell.runMutationState === 'approving' ? 'Approving…' : 'Approve run' }}
          </button>
          <button
            v-if="shell.primaryApprovalRun?.phase === 'awaiting_approval'"
            type="button"
            class="run-actions__button"
            :disabled="!shell.canRejectPrimaryRun"
            @click="shell.rejectPrimaryRun()"
          >
            {{ shell.runMutationState === 'rejecting' ? 'Rejecting…' : 'Reject run' }}
          </button>
        </div>
        <p v-if="shell.primaryApprovalRun?.can_approve" class="region-copy">
          This run is blocked on an explicit approval boundary.
        </p>
      </HudSeamCard>

      <HudSeamCard title="Signals" seam-class="dock-seam dock-seam--signals">
        <strong>{{ shell.inboxStateLabel }}</strong>
        <p v-if="shell.primaryInboxItem" class="region-copy">
          {{ shell.primaryInboxItem.summary }}
        </p>
        <p v-else-if="shell.inboxLoadState === 'error'" class="region-copy">
          {{ shell.inboxError }}
        </p>
      </HudSeamCard>

      <HudSeamCard title="Active Run" seam-class="dock-seam dock-seam--run">
        <strong>{{ shell.runStateLabel }}</strong>
        <div
          v-if="
            shell.primaryActiveRun &&
            (
              shell.primaryActiveRun.can_stop ||
              shell.primaryActiveRun.can_resume ||
              shell.primaryActiveRun.phase === 'executing' ||
              shell.primaryActiveRun.phase === 'review_ready'
            )
          "
          class="run-actions"
        >
          <button
            v-if="shell.primaryActiveRun.phase === 'executing'"
            type="button"
            class="run-actions__button"
            :disabled="!shell.canMarkPrimaryRunReviewReady"
            @click="shell.markPrimaryRunReviewReady()"
          >
            {{ shell.runMutationState === 'reviewing' ? 'Sending to review…' : 'Ready for review' }}
          </button>
          <button
            v-if="shell.primaryActiveRun.can_stop"
            type="button"
            class="run-actions__button"
            :disabled="!shell.canStopPrimaryRun"
            @click="shell.stopPrimaryRun()"
          >
            {{ shell.runMutationState === 'stopping' ? 'Stopping…' : 'Stop run' }}
          </button>
          <button
            v-if="shell.primaryActiveRun.can_resume"
            type="button"
            class="run-actions__button"
            :disabled="!shell.canResumePrimaryRun"
            @click="shell.resumePrimaryRun()"
          >
            {{ shell.runMutationState === 'resuming' ? 'Resuming…' : 'Resume run' }}
          </button>
          <button
            v-if="shell.primaryActiveRun.phase === 'review_ready'"
            type="button"
            class="run-actions__button"
            :disabled="!shell.canCompletePrimaryRun"
            @click="shell.completePrimaryRun()"
          >
            {{ shell.runMutationState === 'completing' ? 'Completing…' : 'Complete run' }}
          </button>
        </div>
        <p v-if="shell.primaryActiveRun" class="region-copy">
          {{ shell.primaryActiveRun.detail }}
        </p>
        <p v-if="shell.primaryActiveRun?.current_step" class="region-copy">
          {{ shell.primaryActiveRun.current_step }}
        </p>
        <p v-if="shell.runMutationError" class="region-copy">
          {{ shell.runMutationError }}
        </p>
        <p v-else-if="shell.runsLoadState === 'error'" class="region-copy">
          {{ shell.runsError }}
        </p>
      </HudSeamCard>

      <HudSeamCard title="Conversation" seam-class="dock-seam dock-seam--thread">
        <strong>{{ shell.threadStateLabel }}</strong>
        <p class="region-copy">Transcript and composer attach here in a later slice.</p>
      </HudSeamCard>

      <HudSeamCard title="Command" seam-class="dock-seam dock-seam--command">
        <label class="command-field">
          <span class="command-field__label">Operator command</span>
          <input
            class="command-field__input"
            type="text"
            placeholder="Direct KAIRO or start a run…"
            disabled
          />
        </label>
      </HudSeamCard>

      <div v-if="shell.showDevSeams" class="contract-row contract-row--dev">
        <span v-for="label in dockContractLabels" :key="label" class="contract-pill">
          {{ label }}
        </span>
      </div>
    </aside>

    <footer class="region region-status-bar">
      <span
        v-for="(item, index) in shell.statusBarItems"
        :key="`${item}-${index}`"
        class="status-pill"
      >
        {{ item }}
      </span>
    </footer>
  </div>
</template>
