<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';

import {
  fetchMachinePulse,
  killMachineProcess,
  runMachineCeoTick,
  type MachinePulse,
} from '../../features/host-context/machine-ceo-api';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const pulse = ref<MachinePulse | null>(null);
const status = ref('');
const busy = ref(false);
let timer: ReturnType<typeof setInterval> | null = null;

const autoOn = computed(
  () => String(shell.operatorPresenceSettings.autonomy_mode || '').toLowerCase() === 'full',
);

const memLine = computed(() => {
  const pct = pulse.value?.health?.memory_percent;
  const avail = pulse.value?.health?.memory_available_mb;
  if (pct == null) {
    return 'Memory —';
  }
  const availPart = avail != null ? ` · ${Math.round(avail)} MB free` : '';
  return `RAM ${Math.round(pct)}%${availPart}`;
});

const topLine = computed(() => {
  const top = pulse.value?.processes?.[0];
  if (!top) {
    return 'No process sample yet';
  }
  return `Top · ${top.name} ${Math.round(top.rss_mb)} MB`;
});

async function refresh(): Promise<void> {
  busy.value = true;
  try {
    if (autoOn.value) {
      const tick = await runMachineCeoTick(true);
      pulse.value = tick.pulse;
      status.value = tick.spoken || tick.pulse.spoken || '';
      // #region agent log
      fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'db8bb4' },
        body: JSON.stringify({
          sessionId: 'db8bb4',
          runId: 'machine-ceo',
          hypothesisId: 'M1',
          location: 'MissionControlMachineCeoStrip.vue:refresh',
          message: 'machine ceo tick',
          data: {
            autoOn: true,
            mem: tick.pulse.health?.memory_percent ?? null,
            top: tick.pulse.processes?.[0]?.name ?? null,
            kills: tick.kills?.length ?? 0,
            recommendations: tick.pulse.recommendations?.length ?? 0,
          },
          timestamp: Date.now(),
        }),
      }).catch(() => {});
      // #endregion
    } else {
      pulse.value = await fetchMachinePulse();
      status.value = pulse.value.spoken || '';
    }
  } catch (error) {
    status.value = error instanceof Error ? error.message : 'Machine pulse failed';
  } finally {
    busy.value = false;
  }
}

async function killRec(pid: number, action: string): Promise<void> {
  busy.value = true;
  try {
    // AUTO path: only allowlisted junk. Manual Review kill: operator confirm tier.
    const result = await killMachineProcess(pid, {
      auto: autoOn.value && action === 'kill',
    });
    status.value = String(result.reason || 'kill requested');
    await refresh();
  } catch (error) {
    status.value = error instanceof Error ? error.message : 'Kill blocked';
    busy.value = false;
  }
}

onMounted(() => {
  void refresh();
  timer = setInterval(() => {
    void refresh();
  }, autoOn.value ? 20_000 : 45_000);
});

watch(autoOn, () => {
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
  <section class="mc-machine-ceo" aria-label="VAXON Machine CEO">
    <header class="mc-machine-ceo__head">
      <p class="mc-machine-ceo__eyebrow">Machine CEO</p>
      <span class="mc-machine-ceo__mode" :data-on="autoOn ? 'true' : 'false'">
        {{ autoOn ? 'AUTO' : 'WATCH' }}
      </span>
    </header>
    <p class="mc-machine-ceo__metrics">
      <span>{{ memLine }}</span>
      <span>{{ topLine }}</span>
    </p>
    <p v-if="status" class="mc-machine-ceo__spoken">{{ status }}</p>
    <ul v-if="pulse?.recommendations?.length" class="mc-machine-ceo__recs">
      <li v-for="item in pulse.recommendations.slice(0, 3)" :key="item.pid">
        <span>{{ item.name }} · {{ Math.round(item.rss_mb) }} MB</span>
        <button
          type="button"
          :disabled="busy"
          @click="void killRec(item.pid, item.action)"
        >
          {{ item.action === 'kill' ? 'Kill' : 'Free RAM' }}
        </button>
      </li>
    </ul>
    <button type="button" class="mc-machine-ceo__refresh" :disabled="busy" @click="void refresh()">
      {{ busy ? 'Scanning…' : 'Scan host' }}
    </button>
  </section>
</template>

<style scoped>
.mc-machine-ceo {
  display: grid;
  gap: 0.35rem;
  padding: 0.5rem 0.55rem;
  border: 1px solid rgba(0, 242, 255, 0.22);
  border-radius: 0.4rem;
  background: rgba(0, 16, 24, 0.55);
}

.mc-machine-ceo__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.mc-machine-ceo__eyebrow {
  margin: 0;
  color: rgba(0, 242, 255, 0.85);
  font: 0.58rem var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.mc-machine-ceo__mode {
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
  border: 1px solid rgba(140, 180, 200, 0.35);
  color: rgba(180, 210, 220, 0.9);
  font: 0.55rem var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.1em;
}

.mc-machine-ceo__mode[data-on='true'] {
  border-color: rgba(80, 255, 180, 0.45);
  color: rgba(160, 255, 210, 0.95);
  background: rgba(0, 40, 28, 0.55);
}

.mc-machine-ceo__metrics {
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 0.75rem;
  color: rgba(220, 240, 248, 0.92);
  font: 0.7rem/1.3 var(--font-ui, system-ui, sans-serif);
}

.mc-machine-ceo__spoken {
  margin: 0;
  color: rgba(160, 200, 215, 0.88);
  font: 0.66rem/1.35 var(--font-ui, system-ui, sans-serif);
}

.mc-machine-ceo__recs {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.25rem;
}

.mc-machine-ceo__recs li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  color: rgba(210, 230, 238, 0.92);
  font: 0.64rem var(--font-ui, system-ui, sans-serif);
}

.mc-machine-ceo__recs button,
.mc-machine-ceo__refresh {
  appearance: none;
  border: 1px solid rgba(0, 242, 255, 0.28);
  border-radius: 999px;
  background: rgba(0, 20, 30, 0.7);
  color: rgba(180, 240, 255, 0.95);
  font: 0.55rem var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 0.22rem 0.5rem;
  cursor: pointer;
}

.mc-machine-ceo__recs button:disabled,
.mc-machine-ceo__refresh:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
