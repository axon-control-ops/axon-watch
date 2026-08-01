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

const headline = computed(() => {
  if (error.value) {
    return error.value;
  }
  if (lastSpoken.value) {
    return lastSpoken.value;
  }
  if (!pack.value) {
    return 'Asking Leads…';
  }
  if (pack.value.advise) {
    return pack.value.advise;
  }
  return `Asked ${pack.value.leads_asked} Leads · no Lead-team plans waiting`;
});

const meta = computed(() => {
  if (!pack.value) {
    return '';
  }
  const waiting = pack.value.awaiting_plan_count;
  if (waiting <= 0) {
    return autoOn.value ? 'Plate clear · VAXON watching' : 'Plate clear';
  }
  return autoOn.value
    ? `${waiting} queued · VAXON clearing`
    : `${waiting} plan${waiting === 1 ? '' : 's'} awaiting engagement`;
});

async function refresh(): Promise<void> {
  busy.value = true;
  try {
    pack.value = await fetchMissionControlCriticalWork(focusedId.value);
    error.value = '';
    // Under AUTO, VAXON owns Lead review close-out — do not leave Engage to the operator.
    if (autoOn.value && (pack.value.awaiting_plan_count ?? 0) > 0) {
      const engaged = await engageMissionControlLeads(5);
      lastSpoken.value = engaged.spoken || '';
      // #region agent log
      fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'db8bb4' },
        body: JSON.stringify({
          sessionId: 'db8bb4',
          runId: 'ceo-engage',
          hypothesisId: 'C2',
          location: 'MissionControlCeoCriticalStrip.vue:refresh',
          message: 'ui auto engage leads',
          data: {
            engaged: engaged.engaged?.length ?? 0,
            remaining: engaged.remaining ?? 0,
            spoken: engaged.spoken ?? '',
          },
          timestamp: Date.now(),
        }),
      }).catch(() => {});
      // #endregion
      pack.value = await fetchMissionControlCriticalWork(focusedId.value);
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Critical-work pack failed';
  } finally {
    busy.value = false;
  }
}

async function onPrimaryAction(): Promise<void> {
  if (autoOn.value) {
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
  if (!workspaceId) {
    return;
  }
  if (shell.currentWorkspace?.workspace_id !== workspaceId) {
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
</script>

<template>
  <section class="mc-ceo-critical" aria-label="VAXON Mission Control critical work">
    <header class="mc-ceo-critical__head">
      <p class="mc-ceo-critical__eyebrow">Mission Control · Ask Leads</p>
      <span class="mc-ceo-critical__meta" :data-auto="autoOn ? 'true' : 'false'">{{ meta }}</span>
    </header>
    <p class="mc-ceo-critical__advise">{{ headline }}</p>
    <div class="mc-ceo-critical__actions">
      <button
        type="button"
        class="mc-ceo-critical__btn"
        :disabled="busy || (!autoOn && !pack?.winner)"
        @click="void onPrimaryAction()"
      >
        {{ autoOn ? (busy ? 'Clearing…' : 'Clear reviews') : 'Open' }}
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
}

.mc-ceo-critical__meta[data-auto='true'] {
  color: rgba(160, 255, 210, 0.92);
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
