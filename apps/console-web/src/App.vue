<script setup lang="ts">
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
          <p class="eyebrow">Axon-Watch</p>
          <h1>Integrated shell skeleton</h1>
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
    </header>

    <aside class="region region-left-sidebar">
      <div class="region-header">
        <div>
          <p class="eyebrow">Left Sidebar</p>
          <h2>Workspace and explorer seam</h2>
        </div>
      </div>

      <p class="region-copy">
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
    </aside>

    <main class="region region-center-workbench">
      <div class="region-header">
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

      <div class="workbench-panels">
        <section class="placeholder-card placeholder-card--surface">
          <p class="placeholder-card__label">Editor surface</p>
          <strong>Monaco host placeholder</strong>
          <p class="region-copy">
            Ready for real editor ownership in a later slice. No editor semantics are defined here.
          </p>
        </section>

        <section class="placeholder-card placeholder-card--surface">
          <p class="placeholder-card__label">Preview surface</p>
          <strong>Browser / diff host placeholder</strong>
          <p class="region-copy">
            Workbench remains one shell in both layout modes. Only emphasis changes.
          </p>
        </section>
      </div>

      <div class="contract-row">
        <span v-for="label in workbenchContractLabels" :key="label" class="contract-pill">
          {{ label }}
        </span>
      </div>
    </main>

    <section class="region region-bottom-panel">
      <div class="region-header">
        <div>
          <p class="eyebrow">Bottom Panel</p>
          <h2>Terminal and runtime strip host</h2>
        </div>
      </div>

      <div class="placeholder-card">
        <p class="placeholder-card__label">Terminal session</p>
        <strong>{{ shell.terminalSessions[0]?.title }}</strong>
        <p class="region-copy">
          xterm integration is intentionally deferred. This shell only preserves the region and state slot.
        </p>
      </div>

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
    </section>

    <aside class="region region-right-dock">
      <div class="region-header">
        <div>
          <p class="eyebrow">Right Dock</p>
          <h2>Agent dock and signal summary host</h2>
        </div>
      </div>

      <div class="placeholder-card">
        <p class="placeholder-card__label">Run seam</p>
        <strong>{{ shell.runStateLabel }}</strong>
        <p v-if="shell.primaryActiveRun" class="region-copy">
          {{ shell.primaryActiveRun.detail }}
        </p>
        <p v-else-if="shell.runsLoadState === 'error'" class="region-copy">
          {{ shell.runsError }}
        </p>
      </div>

      <div class="placeholder-card">
        <p class="placeholder-card__label">Approvals seam</p>
        <strong>{{ shell.approvalStateLabel }}</strong>
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

      <div class="contract-row">
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
