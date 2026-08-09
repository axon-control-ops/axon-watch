<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import { fetchAutonomyStatus, type AutonomyStatusFeed } from '../../api/autonomy-api';
import { fetchWorkspaceLeadPlans, type LeadPlansSnapshot } from '../../api/lead-plans-api';
import { fetchWorkspaceTasks, type WorkspaceTasksSnapshot } from '../../api/tasks-api';
import { fetchWorkspaceCompany } from '../../api/workspace-api';
import type { CompanyRosterSnapshot } from '../../contracts/canonical';
import { buildFleetHealthGridCells } from '../../lib/operator-fleet-health-view';
import {
  buildWorkspaceDetailOverview,
  buildWorkspaceLogEntries,
  buildWorkspaceNextActions,
} from '../../lib/workspace-detail-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const workspaceId = computed(() => shell.workspaceDetailWorkspaceId);
const loadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('idle');
const errorMessage = ref<string | null>(null);
const company = ref<CompanyRosterSnapshot | null>(null);
const tasks = ref<WorkspaceTasksSnapshot | null>(null);
const plans = ref<LeadPlansSnapshot | null>(null);
const autonomy = ref<AutonomyStatusFeed | null>(null);

const cell = computed(() => {
  const id = workspaceId.value;
  if (!id) {
    return null;
  }
  const cells = buildFleetHealthGridCells({
    snapshot: shell.operatorFleetHealth,
    workspaces: shell.workspaces,
    selectedWorkspaceId: id,
  });
  return cells.find((row) => row.workspaceId === id) ?? null;
});

const overview = computed(() =>
  workspaceId.value ? buildWorkspaceDetailOverview(workspaceId.value, cell.value, company.value) : null,
);
const nextActions = computed(() =>
  buildWorkspaceNextActions(tasks.value?.items ?? [], plans.value?.items ?? []),
);
const logEntries = computed(() =>
  buildWorkspaceLogEntries(
    autonomy.value?.pending_critical_decisions ?? [],
    autonomy.value?.recent_receipts ?? [],
  ),
);

async function load(id: string): Promise<void> {
  loadState.value = 'loading';
  errorMessage.value = null;
  try {
    const [companyResult, tasksResult, plansResult, autonomyResult] = await Promise.all([
      fetchWorkspaceCompany(id),
      fetchWorkspaceTasks(id, { limit: 100 }),
      fetchWorkspaceLeadPlans(id, { limit: 10 }),
      fetchAutonomyStatus(id),
    ]);
    if (workspaceId.value !== id) {
      return; // Overlay moved on to a different workspace (or closed) while this was in flight.
    }
    company.value = companyResult;
    tasks.value = tasksResult;
    plans.value = plansResult;
    autonomy.value = autonomyResult;
    loadState.value = 'loaded';
  } catch (error) {
    if (workspaceId.value !== id) {
      return;
    }
    errorMessage.value = error instanceof Error ? error.message : 'Workspace detail request failed';
    loadState.value = 'error';
  }
}

watch(
  workspaceId,
  (id) => {
    if (id) {
      void load(id);
    } else {
      loadState.value = 'idle';
      company.value = null;
      tasks.value = null;
      plans.value = null;
      autonomy.value = null;
    }
  },
  { immediate: true },
);

function close(): void {
  shell.closeWorkspaceDetail();
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    close();
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="workspaceId"
      class="workspace-detail-overlay"
      role="dialog"
      aria-modal="true"
      :aria-label="overview ? `${overview.label} workspace detail` : 'Workspace detail'"
      @keydown="onKeydown"
    >
      <div class="workspace-detail-overlay__scrim" @click="close" />
      <div class="workspace-detail-overlay__panel">
        <header class="workspace-detail-overlay__header">
          <div>
            <p class="workspace-detail-overlay__eyebrow">Workspace detail</p>
            <h2 class="workspace-detail-overlay__title">{{ overview?.label ?? workspaceId }}</h2>
          </div>
          <button
            type="button"
            class="workspace-detail-overlay__close"
            aria-label="Close workspace detail"
            @click="close"
          >
            ×
          </button>
        </header>

        <p v-if="loadState === 'loading'" class="workspace-detail-overlay__status">Loading…</p>
        <p v-else-if="loadState === 'error'" class="workspace-detail-overlay__status workspace-detail-overlay__status--error" role="alert">
          {{ errorMessage }}
        </p>

        <template v-else-if="overview">
          <section class="workspace-detail-overlay__section">
            <h3 class="workspace-detail-overlay__section-title">Overview</h3>
            <dl class="workspace-detail-overlay__overview-grid">
              <div>
                <dt>Status</dt>
                <dd :class="`workspace-detail-overlay__health workspace-detail-overlay__health--${overview.health}`">
                  {{ overview.summary }}
                </dd>
              </div>
              <div v-if="overview.projectRoot">
                <dt>Project root</dt>
                <dd>{{ overview.projectRoot }}</dd>
              </div>
              <div>
                <dt>Team</dt>
                <dd>{{ overview.employeeCount }} employee{{ overview.employeeCount === 1 ? '' : 's' }} · {{ overview.busyCount }} busy</dd>
              </div>
            </dl>
          </section>

          <section class="workspace-detail-overlay__section">
            <h3 class="workspace-detail-overlay__section-title">Next actions</h3>
            <ul v-if="nextActions.length > 0" class="workspace-detail-overlay__action-list">
              <li v-for="action in nextActions" :key="action.id" class="workspace-detail-overlay__action">
                <span class="workspace-detail-overlay__action-label">{{ action.label }}</span>
                <span class="workspace-detail-overlay__action-detail">{{ action.detail }}</span>
                <span class="workspace-detail-overlay__action-owner">{{ action.ownerRole }}</span>
              </li>
            </ul>
            <p v-else class="workspace-detail-overlay__empty">Nothing queued — the team is caught up.</p>
          </section>

          <section class="workspace-detail-overlay__section">
            <h3 class="workspace-detail-overlay__section-title">Full log</h3>
            <ul v-if="logEntries.length > 0" class="workspace-detail-overlay__log-list">
              <li
                v-for="entry in logEntries"
                :key="entry.id"
                class="workspace-detail-overlay__log-entry"
                :class="{ 'workspace-detail-overlay__log-entry--needs-you': entry.needsOperator }"
              >
                <span class="workspace-detail-overlay__log-time">{{ entry.createdAt }}</span>
                <span class="workspace-detail-overlay__log-kind">{{ entry.kind }}</span>
                <span class="workspace-detail-overlay__log-title">{{ entry.title }}</span>
                <span class="workspace-detail-overlay__log-detail">{{ entry.detail }}</span>
                <span v-if="entry.needsOperator" class="workspace-detail-overlay__log-badge">NEEDS YOU</span>
                <span v-else class="workspace-detail-overlay__log-status">{{ entry.status }}</span>
              </li>
            </ul>
            <p v-else class="workspace-detail-overlay__empty">No warnings or errors on record.</p>
          </section>
        </template>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.workspace-detail-overlay {
  position: fixed;
  inset: 0;
  z-index: 900;
  display: flex;
  justify-content: flex-end;
}

.workspace-detail-overlay__scrim {
  position: absolute;
  inset: 0;
  background: rgba(4, 8, 14, 0.6);
}

.workspace-detail-overlay__panel {
  position: relative;
  width: min(560px, 100vw);
  height: 100%;
  overflow-y: auto;
  background: var(--axon-panel-bg, #0b1118);
  border-left: 1px solid var(--axon-border, rgba(255, 255, 255, 0.12));
  padding: 20px 22px 32px;
  box-shadow: -24px 0 48px rgba(0, 0, 0, 0.35);
}

.workspace-detail-overlay__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.workspace-detail-overlay__eyebrow {
  margin: 0 0 4px;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.6;
}

.workspace-detail-overlay__title {
  margin: 0;
  font-size: 20px;
}

.workspace-detail-overlay__close {
  border: none;
  background: transparent;
  color: inherit;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  opacity: 0.7;
  padding: 4px 8px;
}

.workspace-detail-overlay__close:hover {
  opacity: 1;
}

.workspace-detail-overlay__status {
  opacity: 0.75;
}

.workspace-detail-overlay__status--error {
  color: #ff8a8a;
}

.workspace-detail-overlay__section {
  margin-bottom: 24px;
}

.workspace-detail-overlay__section-title {
  font-size: 13px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  opacity: 0.65;
  margin: 0 0 10px;
}

.workspace-detail-overlay__overview-grid {
  display: grid;
  gap: 10px;
  margin: 0;
}

.workspace-detail-overlay__overview-grid dt {
  font-size: 11px;
  opacity: 0.55;
}

.workspace-detail-overlay__overview-grid dd {
  margin: 2px 0 0;
  font-size: 14px;
}

.workspace-detail-overlay__health--nominal {
  color: #6fe3a1;
}

.workspace-detail-overlay__health--attention {
  color: #ffcf6f;
}

.workspace-detail-overlay__health--critical {
  color: #ff7a7a;
}

.workspace-detail-overlay__action-list,
.workspace-detail-overlay__log-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.workspace-detail-overlay__action,
.workspace-detail-overlay__log-entry {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 13px;
}

.workspace-detail-overlay__log-entry--needs-you {
  border-color: rgba(255, 122, 122, 0.5);
  background: rgba(255, 122, 122, 0.08);
}

.workspace-detail-overlay__action-label,
.workspace-detail-overlay__log-title {
  font-weight: 600;
}

.workspace-detail-overlay__action-detail,
.workspace-detail-overlay__log-detail {
  opacity: 0.8;
}

.workspace-detail-overlay__action-owner,
.workspace-detail-overlay__log-time,
.workspace-detail-overlay__log-kind,
.workspace-detail-overlay__log-status {
  font-size: 11px;
  opacity: 0.55;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.workspace-detail-overlay__log-badge {
  align-self: flex-start;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: #ff7a7a;
}

.workspace-detail-overlay__empty {
  opacity: 0.6;
  font-size: 13px;
}
</style>
