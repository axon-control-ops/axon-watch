<script setup lang="ts">
import { onMounted, ref } from 'vue';

import { fetchWorkspaces, fetchWorkspaceComposerPrefs, saveWorkspaceComposerPrefs } from '../../api/workspace-api';
import type { WorkspaceRecord } from '../../contracts/canonical';
import { useShellStore } from '../../stores/shell';

const ALL_RUNTIMES = ['codex', 'claude', 'cursor'];

interface WorkspaceAutonomyRow {
  workspace_id: string;
  display_name: string;
  has_active_team: boolean;
  autoAllowedRuntimes: string[];
  saving: boolean;
}

const loadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('idle');
const errorMessage = ref<string | null>(null);
const rows = ref<WorkspaceAutonomyRow[]>([]);
const shell = useShellStore();

function isOn(row: WorkspaceAutonomyRow): boolean {
  return row.autoAllowedRuntimes.length > 0;
}

async function load(): Promise<void> {
  loadState.value = 'loading';
  errorMessage.value = null;
  try {
    const list = await fetchWorkspaces();
    const withPrefs = await Promise.all(
      list.items.map(async (workspace: WorkspaceRecord) => {
        let autoAllowedRuntimes: string[] = [];
        try {
          const prefs = await fetchWorkspaceComposerPrefs(workspace.workspace_id);
          autoAllowedRuntimes = prefs.auto_allowed_runtimes ?? [];
        } catch {
          autoAllowedRuntimes = [];
        }
        return {
          workspace_id: workspace.workspace_id,
          display_name: workspace.display_name || workspace.workspace_id,
          has_active_team: Boolean(workspace.has_active_team),
          autoAllowedRuntimes,
          saving: false,
        };
      }),
    );
    rows.value = withPrefs;
    loadState.value = 'loaded';
  } catch (error) {
    loadState.value = 'error';
    errorMessage.value = error instanceof Error ? error.message : 'Could not load workspaces.';
  }
}

async function toggleAutonomy(row: WorkspaceAutonomyRow): Promise<void> {
  const nextRuntimes = isOn(row) ? [] : [...ALL_RUNTIMES];
  row.saving = true;
  try {
    const saved = await saveWorkspaceComposerPrefs(row.workspace_id, {
      auto_allowed_runtimes: nextRuntimes,
    });
    row.autoAllowedRuntimes = saved.auto_allowed_runtimes ?? nextRuntimes;
    await shell.loadWorkspaces({ sync: false });
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Toggle failed.';
  } finally {
    row.saving = false;
  }
}

onMounted(() => {
  void load();
});
</script>

<template>
  <div class="workspace-autonomy-toggle">
    <p v-if="loadState === 'loading'" class="workspace-runtime-policy__empty">Loading workspaces…</p>
    <p
      v-if="errorMessage"
      class="settings-feedback-banner settings-feedback-banner--inline settings-feedback-banner--error"
      role="alert"
    >
      {{ errorMessage }}
    </p>

    <template v-if="loadState !== 'loading'">
      <ul class="workspace-autonomy-toggle__list">
        <li
          v-for="row in rows"
          :key="row.workspace_id"
          class="workspace-autonomy-toggle__row"
          :class="{ 'workspace-autonomy-toggle__row--on': isOn(row) }"
        >
          <span class="workspace-autonomy-toggle__copy">
            <span class="workspace-autonomy-toggle__label">{{ row.display_name }}</span>
            <span class="workspace-autonomy-toggle__hint">
              {{ row.has_active_team ? 'Staffed' : 'No active team' }}
              ·
              {{ isOn(row) ? `AUTO dispatch: ${row.autoAllowedRuntimes.join(', ')}` : 'AUTO dispatch off' }}
            </span>
          </span>
          <button
            type="button"
            class="workspace-autonomy-toggle__switch"
            role="switch"
            :aria-checked="isOn(row)"
            :aria-label="`Toggle AUTO dispatch for ${row.display_name}`"
            :disabled="row.saving"
            @click="toggleAutonomy(row)"
          >
            <span class="workspace-autonomy-toggle__switch-knob" />
          </button>
        </li>
      </ul>

      <p class="workspace-runtime-policy__note" role="note">
        On enables all three runtimes (Codex, Claude, Cursor) for AUTO dispatch in that
        workspace. Off blocks the continuous worker scheduler entirely — Leads there will
        sit at "Start now" until you either flip this on or start their shift manually.
        For fine-grained per-runtime control of the current workspace, use the panel below.
      </p>
    </template>
  </div>
</template>
