<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';

import {
  engageMissionControlLeads,
  fetchMissionControlCriticalWork,
  type MissionControlCriticalWork,
} from '../../features/mission-control/mission-control-ceo-api';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const pack = ref<MissionControlCriticalWork | null>(null);
const error = ref('');
const busy = ref(false);
const lastSpoken = ref('');
let timer: ReturnType<typeof setInterval> | null = null;

const focusedId = computed(() => shell.currentWorkspace?.workspace_id ?? null);
const autoOn = computed(
  () => String(shell.operatorPresenceSettings.autonomy_mode || '').toLowerCase() === 'full',
);

const plate = computed(() => pack.value?.plate ?? null);
const plateLoad = computed(() => String(plate.value?.load || 'idle'));
const plateOpen = computed(() => Number(plate.value?.total_open_plate || 0));

const headline = computed(() => {
  if (error.value) {
    return error.value;
  }
  if (lastSpoken.value && (pack.value?.awaiting_plan_count ?? 0) > 0) {
    return lastSpoken.value;
  }
  if (!pack.value) {
    return 'Asking Leads…';
  }
  if (pack.value.advise) {
    return pack.value.advise;
  }
  if (plateOpen.value > 0) {
    return 'Board still has work — scanning plate…';
  }
  return `Asked ${pack.value.leads_asked} Leads · plate clear`;
});

const meta = computed(() => {
  if (!pack.value) {
    return '';
  }
  const plans = pack.value.awaiting_plan_count ?? 0;
  const waiting = plate.value?.waiting ?? 0;
  const needs = plate.value?.needs_attention ?? 0;
  const live = plate.value?.in_progress ?? 0;
  const cross = plate.value?.cross_workspace ?? 0;
  if (plans > 0) {
    return autoOn.value
      ? `${plans} Lead review${plans === 1 ? '' : 's'} · clearing`
      : `${plans} Lead review${plans === 1 ? '' : 's'} waiting`;
  }
  if (plateOpen.value > 0) {
    const bits = [
      waiting ? `${waiting} waiting` : '',
      live ? `${live} live` : '',
      needs ? `${needs} review` : '',
      cross ? `${cross} cross-ws` : '',
    ].filter(Boolean);
    return bits.join(' · ') || `${plateOpen.value} on plate`;
  }
  return autoOn.value ? 'Plate clear · watching' : 'Plate clear';
});

async function refresh(): Promise<void> {
  busy.value = true;
  try {
    pack.value = await fetchMissionControlCriticalWork(focusedId.value);
    error.value = '';
    if (autoOn.value && (pack.value.awaiting_plan_count ?? 0) > 0) {
      const engaged = await engageMissionControlLeads(5);
      lastSpoken.value = engaged.spoken || '';
      pack.value = await fetchMissionControlCriticalWork(focusedId.value);
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Critical-work pack failed';
  } finally {
    busy.value = false;
  }
}

async function onPrimaryAction(): Promise<void> {
  if (autoOn.value && (pack.value?.awaiting_plan_count ?? 0) > 0) {
    busy.value = true;
    try {
      const engaged = await engageMissionControlLeads(5);
      lastSpoken.value = engaged.spoken || '';
      pack.value = await fetchMissionControlCriticalWork(focusedId.value);
      error.value = '';
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Engage failed';
    } finally {
      busy.value = false;
    }
    return;
  }
  const action = pack.value?.advise_ui_action;
  const workspaceId = action?.workspace_id?.trim();
  if (workspaceId && shell.currentWorkspace?.workspace_id !== workspaceId) {
    shell.setCurrentWorkspace(workspaceId);
  }
  shell.focusMissionControl();
  shell.focusAttentionSidebar();
}

onMounted(() => {
  void refresh();
  timer = setInterval(() => {
    void refresh();
  }, 30_000);
});

watch([focusedId, autoOn], () => {
  void refresh();
});

onUnmounted(() => {
  if (timer) {
    clearInterval(timer);
    timer = null;
  }
});

defineExpose({ plateLoad, pack });
</script>

<template>
  <section
    class="mc-ceo-critical"
    aria-label="VAXON Mission Control critical work"
    :data-load="plateLoad"
  >
    <header class="mc-ceo-critical__head">
      <p class="mc-ceo-critical__eyebrow">Mission Control · Ask Leads</p>
      <span
        class="mc-ceo-critical__meta"
        :data-auto="autoOn ? 'true' : 'false'"
        :data-load="plateLoad"
      >
        {{ meta }}
      </span>
    </header>
    <p class="mc-ceo-critical__advise">{{ headline }}</p>
    <div class="mc-ceo-critical__actions">
      <button
        type="button"
        class="mc-ceo-critical__btn"
        :disabled="busy || (!autoOn && !pack?.advise && !pack?.winner)"
        @click="void onPrimaryAction()"
      >
        {{
          autoOn && (pack?.awaiting_plan_count ?? 0) > 0
            ? busy
              ? 'Clearing…'
              : 'Clear reviews'
            : plateOpen > 0
              ? 'Open board'
              : 'Open'
        }}
      </button>
      <button
        type="button"
        class="mc-ceo-critical__btn mc-ceo-critical__btn--ghost"
        :disabled="busy"
        @click="void refresh()"
      >
        {{ busy ? 'Working…' : autoOn ? 'Scan + act' : 'Ask Leads' }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.mc-ceo-critical {
  display: grid;
  gap: 0.35rem;
  flex: 0 0 auto;
  margin: 0 0 0.25rem;
  padding: 0.55rem 0.65rem;
  border: 1px solid rgba(255, 190, 90, 0.35);
  border-radius: 0.45rem;
  background:
    linear-gradient(120deg, rgba(40, 28, 0, 0.55), rgba(0, 16, 28, 0.78)),
    rgba(0, 16, 24, 0.7);
  transition:
    border-color 220ms ease,
    box-shadow 220ms ease;
}

.mc-ceo-critical[data-load='busy'] {
  border-color: rgba(0, 220, 255, 0.4);
}

.mc-ceo-critical[data-load='critical'] {
  border-color: rgba(255, 120, 90, 0.55);
  box-shadow: 0 0 0 1px rgba(255, 90, 60, 0.18);
}

.mc-ceo-critical__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.mc-ceo-critical__eyebrow {
  margin: 0;
  color: rgba(255, 210, 140, 0.95);
  font: 0.62rem var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.mc-ceo-critical__meta {
  color: rgba(200, 220, 230, 0.75);
  font: 0.58rem var(--font-mono, ui-monospace, monospace);
  text-align: right;
}

.mc-ceo-critical__meta[data-auto='true'] {
  color: rgba(160, 255, 210, 0.92);
}

.mc-ceo-critical__meta[data-load='critical'] {
  color: rgba(255, 180, 140, 0.95);
}

.mc-ceo-critical__advise {
  margin: 0;
  color: rgba(235, 245, 250, 0.95);
  font: 0.72rem/1.35 var(--font-ui, system-ui, sans-serif);
}

.mc-ceo-critical__actions {
  display: flex;
  gap: 0.4rem;
}

.mc-ceo-critical__btn {
  appearance: none;
  border: 1px solid rgba(255, 190, 90, 0.4);
  border-radius: 999px;
  background: rgba(40, 28, 0, 0.75);
  color: rgba(255, 230, 180, 0.98);
  font: 0.55rem var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 0.22rem 0.55rem;
  cursor: pointer;
}

.mc-ceo-critical__btn--ghost {
  border-color: rgba(0, 242, 255, 0.28);
  background: rgba(0, 20, 30, 0.7);
  color: rgba(180, 240, 255, 0.95);
}

.mc-ceo-critical__btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
