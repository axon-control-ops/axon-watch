<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import WorkspaceAddForm from '../../components/shell/WorkspaceAddForm.vue';
import { fetchWorkspaceComposerPrefs, saveWorkspaceComposerPrefs } from '../../api/workspace-api';
import type { BrainGraphSnapshot } from '../../lib/operator-brain-graph-view';
import type { FleetHealthSnapshot } from '../../lib/operator-fleet-health-view';
import type { WorkspaceRecord } from '../../contracts/canonical';
import { useShellStore } from '../../stores/shell';
import type { GalaxyMockupRailItem } from './galaxy-mockup-rail-view';
import { galaxyMockupRailItemsWithChips } from './galaxy-workspaces-rail-view';

const ALL_AUTO_RUNTIMES = ['codex', 'claude', 'cursor'];

const props = defineProps<{
  snapshot: BrainGraphSnapshot | null;
  workspaces: WorkspaceRecord[];
  selectedId: string | null;
  currentWorkspaceId: string | null;
  fleetHealth?: FleetHealthSnapshot | null;
  collapsed?: boolean;
}>();

const emit = defineEmits<{
  select: [item: GalaxyMockupRailItem];
  open: [item: GalaxyMockupRailItem];
  toggleCollapse: [];
}>();

const query = ref('');
const showAddForm = ref(false);
const shell = useShellStore();

const items = computed(() =>
  galaxyMockupRailItemsWithChips(
    props.snapshot,
    props.workspaces,
    props.fleetHealth ?? null,
  ).filter((item) => {
    const q = query.value.trim().toLowerCase();
    if (!q) {
      return true;
    }
    return (
      item.label.toLowerCase().includes(q) ||
      (item.workspace_id || '').toLowerCase().includes(q)
    );
  }),
);

function isActive(item: GalaxyMockupRailItem): boolean {
  if (props.selectedId && props.selectedId === item.id) {
    return true;
  }
  if (item.kind === 'workspace' && item.workspace_id && props.currentWorkspaceId) {
    return item.workspace_id === props.currentWorkspaceId && !props.selectedId;
  }
  return false;
}

function onOpen(event: Event, item: GalaxyMockupRailItem): void {
  event.stopPropagation();
  emit('open', item);
}

const autonomyByWorkspace = ref<Record<string, string[]>>({});
const autonomySaving = ref<Record<string, boolean>>({});

function isAutonomyOn(workspaceId: string): boolean {
  return (autonomyByWorkspace.value[workspaceId] ?? []).length > 0;
}

async function loadAutonomy(): Promise<void> {
  const ids = props.workspaces.map((w) => w.workspace_id);
  const results = await Promise.allSettled(ids.map((id) => fetchWorkspaceComposerPrefs(id)));
  const next: Record<string, string[]> = {};
  ids.forEach((id, index) => {
    const result = results[index];
    next[id] = result.status === 'fulfilled' ? (result.value.auto_allowed_runtimes ?? []) : [];
  });
  autonomyByWorkspace.value = next;
}

async function toggleAutonomy(event: Event, workspaceId: string): Promise<void> {
  event.stopPropagation();
  if (autonomySaving.value[workspaceId]) {
    return;
  }
  const nextRuntimes = isAutonomyOn(workspaceId) ? [] : [...ALL_AUTO_RUNTIMES];
  autonomySaving.value = { ...autonomySaving.value, [workspaceId]: true };
  try {
    const saved = await saveWorkspaceComposerPrefs(workspaceId, { auto_allowed_runtimes: nextRuntimes });
    autonomyByWorkspace.value = {
      ...autonomyByWorkspace.value,
      [workspaceId]: saved.auto_allowed_runtimes ?? nextRuntimes,
    };
    await shell.loadWorkspaces({ sync: false });
  } finally {
    autonomySaving.value = { ...autonomySaving.value, [workspaceId]: false };
  }
}

onMounted(() => {
  void loadAutonomy();
});
</script>

<template>
  <aside
    class="galaxy-workspaces-rail"
    :class="{ 'galaxy-workspaces-rail--collapsed': collapsed }"
    aria-label="Workspaces"
  >
    <header class="galaxy-workspaces-rail__header">
      <button
        type="button"
        class="galaxy-workspaces-rail__collapse"
        :aria-expanded="!collapsed"
        :title="collapsed ? 'Expand workspaces' : 'Collapse workspaces'"
        :aria-label="collapsed ? 'Expand workspaces' : 'Collapse workspaces'"
        @click="emit('toggleCollapse')"
      >
        <span class="galaxy-workspaces-rail__collapse-chevron" aria-hidden="true" />
      </button>
      <p v-if="!collapsed" class="galaxy-workspaces-rail__title">Workspaces</p>
      <button
        v-if="!collapsed"
        type="button"
        class="galaxy-workspaces-rail__add-icon"
        title="New workspace"
        aria-label="New workspace"
        @click="showAddForm = true"
      >
        +
      </button>
    </header>

    <button
      v-if="collapsed"
      type="button"
      class="galaxy-workspaces-rail__collapsed-label"
      title="Expand workspaces"
      aria-label="Expand workspaces"
      @click="emit('toggleCollapse')"
    >
      Workspaces
    </button>

    <template v-if="!collapsed">
      <label class="galaxy-workspaces-rail__search">
        <span class="galaxy-workspaces-rail__search-icon" aria-hidden="true">⌕</span>
        <input
          v-model="query"
          type="search"
          placeholder="Search workspaces…"
          autocomplete="off"
        />
      </label>

      <ul class="galaxy-workspaces-rail__list">
        <li v-for="item in items" :key="item.id">
          <div
            class="galaxy-workspaces-rail__row"
            :class="{ 'galaxy-workspaces-rail__row--active': isActive(item) }"
          >
            <button
              type="button"
              class="galaxy-workspaces-rail__item"
              :class="[
                `galaxy-workspaces-rail__item--${item.tone}`,
                { 'galaxy-workspaces-rail__item--active': isActive(item) },
              ]"
              @click="emit('select', item)"
            >
              <span
                class="galaxy-workspaces-rail__glyph"
                :class="`galaxy-workspaces-rail__glyph--${item.icon}`"
                aria-hidden="true"
              />
              <span class="galaxy-workspaces-rail__copy">
                <strong>{{ item.label }}</strong>
                <span>{{ item.detail }}</span>
                <span v-if="item.chips.length" class="galaxy-workspaces-rail__chips">
                  <span
                    v-for="chip in item.chips"
                    :key="chip.id"
                    class="galaxy-workspaces-rail__chip"
                    :class="`galaxy-workspaces-rail__chip--${chip.tone}`"
                  >
                    {{ chip.label }}
                  </span>
                </span>
              </span>
              <span v-if="item.kind !== 'workspace'" class="galaxy-workspaces-rail__dot" aria-hidden="true" />
            </button>
            <button
              v-if="item.kind === 'workspace' && item.workspace_id"
              type="button"
              class="galaxy-workspaces-rail__autonomy-switch"
              role="switch"
              :aria-checked="isAutonomyOn(item.workspace_id)"
              :aria-label="`Toggle AUTO dispatch for ${item.label}`"
              :disabled="autonomySaving[item.workspace_id]"
              :class="{ 'galaxy-workspaces-rail__autonomy-switch--on': isAutonomyOn(item.workspace_id) }"
              title="AUTO dispatch on/off"
              @click="toggleAutonomy($event, item.workspace_id)"
            >
              <span class="galaxy-workspaces-rail__autonomy-switch-knob" />
            </button>
            <button
              v-if="item.kind === 'workspace'"
              type="button"
              class="galaxy-workspaces-rail__open"
              :class="{ 'galaxy-workspaces-rail__open--visible': isActive(item) }"
              title="Open workspace"
              :aria-label="`Open ${item.label}`"
              @click="onOpen($event, item)"
            >
              Open
            </button>
          </div>
        </li>
      </ul>

      <WorkspaceAddForm
        v-if="showAddForm"
        @registered="showAddForm = false"
        @cancel="showAddForm = false"
      />
      <button
        v-else
        type="button"
        class="galaxy-workspaces-rail__new"
        @click="showAddForm = true"
      >
        + New Workspace
      </button>
    </template>
  </aside>
</template>
