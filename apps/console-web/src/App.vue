<script setup lang="ts">
import EditorHost from './components/EditorHost.vue';
import TerminalHost from './components/TerminalHost.vue';
import { useShellStore } from './stores/shell';

const shell = useShellStore();

const workbenchContractLabels = ['WorkspaceRecord', 'RunRecord'];
const dockContractLabels = ['RunRecord', 'ApprovalRecord', 'InboxItem', 'SignalView', 'ThreadMessage'];
const statusContractLabels = ['RuntimeSummary', 'WorkspaceRecord'];
</script>

<template>
  <div class="console-shell" :data-layout-mode="shell.layoutMode">
    <header class="region region-topbar">
      <div class="region-header">
        <div>
          <p class="eyebrow">Axon-X</p>
          <h1>Operator console</h1>
        </div>

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

      <div class="chip-row">
        <span class="chip">{{ shell.layoutModeLabel }}</span>
        <span class="chip">{{ shell.runtimeStateLabel }}</span>
        <span class="chip">{{ shell.runStateLabel }}</span>
      </div>

      <p class="smoke-banner">
        Smoke test: pick a <strong>workspace</strong> (left) → read the <strong>Workspace Overview</strong>
        editor (center) → in the terminal below run <code>pwd</code> then <code>echo hello</code>.
      </p>
    </header>

    <aside class="region region-left-sidebar">
      <div class="region-header dev-scaffold">
        <div>
          <p class="eyebrow">Left Sidebar</p>
          <h2>Workspace and explorer seam</h2>
        </div>
      </div>

      <p class="region-copy dev-scaffold">
        Hosts workspace navigation and explorer ownership without asserting workspace semantics locally.
      </p>

      <div class="placeholder-card">
        <p class="placeholder-card__label">Canonical seam</p>
        <strong>{{ shell.workspaceStateLabel }}</strong>
      </div>

      <div class="placeholder-card">
        <p class="placeholder-card__label">Shell state</p>
        <strong>{{ shell.workspaces.length }} canonical workspace records loaded</strong>
      </div>

      <div class="placeholder-card">
        <p class="placeholder-card__label">Workspace navigation</p>
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
      </div>
    </aside>

    <main class="region region-center-workbench">
      <div class="region-header dev-scaffold">
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
          :class="{ 'tab-strip__tab--active': shell.activeEditorDocumentId === document.id }"
          @click="shell.setActiveEditorDocument(document.id)"
        >
          {{ document.title }}
        </button>
      </div>

      <div class="workbench-panels workbench-panels--single">
        <section
          v-if="shell.activeEditorTabId === 'editor-shell'"
          class="placeholder-card placeholder-card--surface placeholder-card--host"
        >
          <EditorHost
            v-if="shell.activeEditorDocument"
            :title="shell.activeEditorDocument.title"
            :value="shell.activeEditorDocument.value"
            :language="shell.activeEditorDocument.language"
            :description="shell.activeEditorDocument.description"
          />
        </section>

        <section
          v-else
          class="placeholder-card placeholder-card--surface"
        >
          <p class="placeholder-card__label">Preview surface</p>
          <strong>Browser / diff host placeholder</strong>
          <p class="region-copy">
            Workbench remains one shell in both layout modes. Only emphasis changes.
          </p>
        </section>
      </div>

      <div class="contract-row contract-row--dev">
        <span v-for="label in workbenchContractLabels" :key="label" class="contract-pill">
          {{ label }}
        </span>
      </div>
    </main>

    <section class="region region-bottom-panel">
      <div class="region-header dev-scaffold">
        <div>
          <p class="eyebrow">Bottom Panel</p>
          <h2>Terminal and runtime strip host</h2>
        </div>
      </div>

      <div class="bottom-panel-grid">
        <section class="placeholder-card placeholder-card--host">
          <p class="placeholder-card__label">Terminal — backend PTY</p>
          <TerminalHost
            :workspace-id="shell.currentWorkspace?.workspace_id ?? null"
            :run-summary="shell.primaryActiveRun ? `${shell.primaryActiveRun.run_id} · ${shell.primaryActiveRun.phase} · ${shell.primaryActiveRun.status}` : null"
            :primary-signal-id="shell.workspacePrimarySignal?.signal_id ?? null"
            :runtime-connected="Boolean(shell.runtimeSummary?.watch.connected)"
          />
        </section>

        <div v-if="shell.runtimeSummary" class="placeholder-card">
          <p class="placeholder-card__label">Runtime summary</p>
          <strong>
            {{ shell.runtimeSummary.runtime_identity.provider_name }} /
            {{ shell.runtimeSummary.runtime_identity.model_name }}
          </strong>
          <p class="region-copy">
            {{ shell.runtimeSummary.active_runs.length }} active run(s),
            {{ shell.runtimeSummary.signals.open_count }} open signal(s),
            degraded={{ shell.runtimeSummary.degraded.active }}.
          </p>
        </div>

        <div v-else-if="shell.runtimeSummaryLoadState === 'error'" class="placeholder-card">
          <p class="placeholder-card__label">Runtime summary</p>
          <strong>Unavailable</strong>
          <p class="region-copy">{{ shell.runtimeSummaryError }}</p>
        </div>
      </div>
    </section>

    <aside class="region region-right-dock">
      <div class="region-header dev-scaffold">
        <div>
          <p class="eyebrow">Right Dock</p>
          <h2>Agent dock and signal summary host</h2>
        </div>
      </div>

      <div class="placeholder-card">
        <p class="placeholder-card__label">Run seam</p>
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
            {{ shell.runMutationState === 'reviewing' ? 'Sending to review...' : 'Ready for review' }}
          </button>
          <button
            v-if="shell.primaryActiveRun.can_stop"
            type="button"
            class="run-actions__button"
            :disabled="!shell.canStopPrimaryRun"
            @click="shell.stopPrimaryRun()"
          >
            {{ shell.runMutationState === 'stopping' ? 'Stopping...' : 'Stop run' }}
          </button>
          <button
            v-if="shell.primaryActiveRun.can_resume"
            type="button"
            class="run-actions__button"
            :disabled="!shell.canResumePrimaryRun"
            @click="shell.resumePrimaryRun()"
          >
            {{ shell.runMutationState === 'resuming' ? 'Resuming...' : 'Resume run' }}
          </button>
          <button
            v-if="shell.primaryActiveRun.phase === 'review_ready'"
            type="button"
            class="run-actions__button"
            :disabled="!shell.canCompletePrimaryRun"
            @click="shell.completePrimaryRun()"
          >
            {{ shell.runMutationState === 'completing' ? 'Completing...' : 'Complete run' }}
          </button>
        </div>
        <p v-if="shell.primaryActiveRun" class="region-copy">
          {{ shell.primaryActiveRun.detail }}
        </p>
        <p v-if="shell.primaryActiveRun?.current_step" class="region-copy">
          step={{ shell.primaryActiveRun.current_step }}
        </p>
        <p v-if="shell.runMutationError" class="region-copy">
          {{ shell.runMutationError }}
        </p>
        <p v-else-if="shell.runsLoadState === 'error'" class="region-copy">
          {{ shell.runsError }}
        </p>
      </div>

      <div class="placeholder-card">
        <p class="placeholder-card__label">Approvals seam</p>
        <strong>{{ shell.approvalStateLabel }}</strong>
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
            {{ shell.runMutationState === 'approving' ? 'Approving...' : 'Approve run' }}
          </button>
          <button
            v-if="shell.primaryApprovalRun?.phase === 'awaiting_approval'"
            type="button"
            class="run-actions__button"
            :disabled="!shell.canRejectPrimaryRun"
            @click="shell.rejectPrimaryRun()"
          >
            {{ shell.runMutationState === 'rejecting' ? 'Rejecting...' : 'Reject run' }}
          </button>
        </div>
        <p v-if="shell.primaryApprovalRun?.can_approve" class="region-copy">
          {{ shell.primaryApprovalRun.run_id }} is blocked on an explicit approval boundary.
        </p>
      </div>

      <div class="placeholder-card">
        <p class="placeholder-card__label">Signals seam</p>
        <strong>{{ shell.inboxStateLabel }}</strong>
        <p v-if="shell.primaryInboxItem" class="region-copy">
          {{ shell.primaryInboxItem.title }} — {{ shell.primaryInboxItem.summary }}
        </p>
        <p v-else-if="shell.inboxLoadState === 'error'" class="region-copy">
          {{ shell.inboxError }}
        </p>
      </div>

      <div class="placeholder-card">
        <p class="placeholder-card__label">Thread seam</p>
        <strong>{{ shell.threadStateLabel }}</strong>
        <p class="region-copy">One future composer model lives here, but no composer logic is duplicated in this slice.</p>
      </div>

      <div class="contract-row contract-row--dev">
        <span v-for="label in dockContractLabels" :key="label" class="contract-pill">
          {{ label }}
        </span>
      </div>
    </aside>

    <footer class="region region-status-bar">
      <span>Status bar shell</span>
      <span>{{ shell.layoutMode }}</span>
      <span>{{ shell.dockContext.title }}</span>
      <span>{{ shell.runtimeStateLabel }}</span>
      <span v-for="label in statusContractLabels" :key="label" class="status-pill">{{ label }}</span>
    </footer>
  </div>
</template>
