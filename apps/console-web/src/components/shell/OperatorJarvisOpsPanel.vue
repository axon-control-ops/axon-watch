<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue';

import { buildJarvisOpsView } from '../../lib/operator-jarvis-ops-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
let fleetTaskRefreshTimer: ReturnType<typeof setInterval> | null = null;

const fleetTasks = computed(() => Object.values(shell.workspaceTasksById).flat());
const workspaceNamesById = computed(() =>
  Object.fromEntries(
    shell.workspaces.map((workspace) => [
      workspace.workspace_id,
      workspace.display_name || workspace.workspace_id,
    ]),
  ),
);

async function refreshFleetTasks(): Promise<void> {
  await Promise.all(
    shell.workspaces.map((workspace) => shell.loadWorkspaceTasks(workspace.workspace_id)),
  );
}

const view = computed(() =>
  buildJarvisOpsView({
    briefing: shell.operatorBriefing,
    primaryActiveRun: shell.primaryActiveRun,
    fleetActiveRuns: shell.runtimeSummary?.active_runs ?? shell.operatorBriefing?.active_runs ?? [],
    ideComposerActivity: shell.ideComposerActivity,
    employees: shell.companyEmployeesFleet,
    agentStreamActive: shell.agentStreamActive,
    workspaceTasks: fleetTasks.value,
    workspaceNamesById: workspaceNamesById.value,
  }),
);

function onCardActivate(kind: string, id: string): void {
  if (kind === 'command') {
    shell.focusCommandSeam();
    return;
  }
  if (kind === 'agent') {
    shell.revealTeamRosterForActiveEmployee();
    return;
  }
  if (kind === 'task') {
    return;
  }
  shell.focusMissionControl();
}

onMounted(() => {
  void refreshFleetTasks();
  fleetTaskRefreshTimer = setInterval(() => {
    void refreshFleetTasks();
  }, 15_000);
});

onBeforeUnmount(() => {
  if (fleetTaskRefreshTimer) {
    clearInterval(fleetTaskRefreshTimer);
    fleetTaskRefreshTimer = null;
  }
});
</script>

<template>
  <div class="jarvis-ops" aria-label="VAXON operations panel">
    <header class="jarvis-ops__header">
      <p class="jarvis-ops__eyebrow">VAXON // OPS</p>
      <p class="jarvis-ops__headline">{{ view.headline }}</p>
    </header>
    <section
      class="jarvis-ops__activity"
      :data-state="view.activity.state"
      aria-live="polite"
    >
      <span class="jarvis-ops__activity-pulse" aria-hidden="true" />
      <div>
        <p class="jarvis-ops__activity-label">{{ view.activity.label }}</p>
        <p class="jarvis-ops__activity-detail">{{ view.activity.detail }}</p>
      </div>
    </section>
    <p v-if="view.cards.length === 0" class="jarvis-ops__empty">
      No live runs, polls, or agent work right now. Terminal remains available on the TERMINAL tab.
    </p>
    <ul v-else class="jarvis-ops__grid">
      <li
        v-for="card in view.cards"
        :key="card.id"
        class="jarvis-ops__card"
        :data-kind="card.kind"
        :data-tone="card.tone"
      >
        <button
          type="button"
          class="jarvis-ops__card-btn"
          @click="onCardActivate(card.kind, card.id)"
        >
          <span class="jarvis-ops__kind">{{ card.kind }}</span>
          <span class="jarvis-ops__title">{{ card.title }}</span>
          <span class="jarvis-ops__detail">{{ card.detail }}</span>
          <span v-if="card.meta" class="jarvis-ops__meta">{{ card.meta }}</span>
        </button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.jarvis-ops {
  height: 100%;
  min-height: 0;
  overflow: auto;
  padding: 0.75rem 1rem 1rem;
  background:
    radial-gradient(ellipse at 10% 0%, rgba(0, 140, 200, 0.12), transparent 45%),
    linear-gradient(180deg, rgba(6, 14, 22, 0.96), rgba(4, 10, 16, 0.98));
}

.jarvis-ops__header {
  margin-bottom: 0.75rem;
}

.jarvis-ops__eyebrow {
  margin: 0;
  color: rgba(120, 210, 255, 0.72);
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace);
  font-size: 0.62rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.jarvis-ops__headline {
  margin: 0.2rem 0 0;
  color: rgba(230, 246, 255, 0.94);
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace);
  font-size: 0.86rem;
  letter-spacing: 0.02em;
}

.jarvis-ops__activity {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  margin: 0 0 0.75rem;
  padding: 0.55rem 0.7rem;
  border: 1px solid rgba(100, 180, 220, 0.25);
  border-radius: 0.55rem;
  background: rgba(10, 24, 36, 0.75);
}

.jarvis-ops__activity[data-state='active'] {
  border-color: rgba(56, 220, 160, 0.48);
  background: rgba(10, 48, 40, 0.62);
}

.jarvis-ops__activity[data-state='queued'] {
  border-color: rgba(255, 190, 90, 0.4);
}

.jarvis-ops__activity-pulse {
  flex: 0 0 auto;
  width: 0.55rem;
  height: 0.55rem;
  margin-top: 0.18rem;
  border-radius: 999px;
  background: rgba(140, 190, 210, 0.72);
}

.jarvis-ops__activity[data-state='active'] .jarvis-ops__activity-pulse {
  background: #38dca0;
  box-shadow: 0 0 0 0.22rem rgba(56, 220, 160, 0.16), 0 0 0.8rem rgba(56, 220, 160, 0.55);
}

.jarvis-ops__activity[data-state='queued'] .jarvis-ops__activity-pulse {
  background: #f6bd60;
}

.jarvis-ops__activity-label,
.jarvis-ops__activity-detail {
  margin: 0;
}

.jarvis-ops__activity-label {
  color: rgba(235, 248, 255, 0.96);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.jarvis-ops__activity-detail {
  margin-top: 0.18rem;
  color: rgba(180, 218, 232, 0.78);
  font-size: 0.68rem;
  line-height: 1.35;
}

.jarvis-ops__empty {
  margin: 0;
  color: rgba(160, 190, 210, 0.72);
  font-size: 0.78rem;
  line-height: 1.4;
}

.jarvis-ops__grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
  gap: 0.55rem;
}

.jarvis-ops__card-btn {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.2rem;
  padding: 0.55rem 0.65rem;
  border-radius: 0.55rem;
  border: 1px solid rgba(100, 180, 220, 0.22);
  background: rgba(10, 24, 36, 0.72);
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.jarvis-ops__card-btn:hover {
  border-color: rgba(120, 220, 255, 0.45);
  background: rgba(14, 36, 52, 0.88);
}

.jarvis-ops__card[data-tone='attention'] .jarvis-ops__card-btn {
  border-color: rgba(255, 180, 90, 0.4);
}

.jarvis-ops__card[data-tone='critical'] .jarvis-ops__card-btn {
  border-color: rgba(255, 110, 90, 0.45);
}

.jarvis-ops__kind {
  color: rgba(120, 210, 255, 0.7);
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace);
  font-size: 0.58rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.jarvis-ops__title {
  color: rgba(235, 248, 255, 0.95);
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.2;
}

.jarvis-ops__detail {
  color: rgba(170, 210, 230, 0.78);
  font-size: 0.7rem;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.jarvis-ops__meta {
  color: rgba(140, 190, 210, 0.65);
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace);
  font-size: 0.6rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
</style>
