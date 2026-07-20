<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';

import {
  fetchWorkerSchedulerStatus,
  patchWorkerScheduler,
  stopActiveWorkerRuns,
  type WorkerSchedulerStatus,
} from '../../api/worker-scheduler-api';
import { navigateToAppSurface } from '../../lib/app-surface-route';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const status = ref<WorkerSchedulerStatus | null>(null);
const loadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('idle');
const saving = ref(false);
const stopping = ref(false);
const actionMessage = ref<string | null>(null);
const actionTone = ref<'idle' | 'ok' | 'error' | 'pending' | 'warn'>('idle');
let refreshTimer: ReturnType<typeof setInterval> | null = null;

const effectiveLabel = computed(() => {
  if (!status.value) {
    return 'Unknown';
  }
  if (status.value.blocked_by_env) {
    return 'Blocked by env brake';
  }
  return status.value.effective_enabled ? 'Running' : 'Paused';
});

const effectiveTone = computed(() => {
  if (!status.value) {
    return 'unknown';
  }
  if (status.value.blocked_by_env) {
    return 'blocked';
  }
  return status.value.effective_enabled ? 'running' : 'paused';
});

async function reload(): Promise<void> {
  loadState.value = status.value ? loadState.value : 'loading';
  if (!status.value) {
    actionTone.value = 'idle';
    actionMessage.value = null;
  }
  try {
    status.value = await fetchWorkerSchedulerStatus();
    loadState.value = 'loaded';
  } catch (error) {
    loadState.value = 'error';
    actionTone.value = 'error';
    actionMessage.value =
      error instanceof Error ? error.message : 'Could not load agent fleet status';
  }
}

async function persist(patch: {
  scheduler_enabled?: boolean;
  max_active?: number;
  max_starts_per_tick?: number;
}): Promise<void> {
  saving.value = true;
  actionTone.value = 'pending';
  actionMessage.value = 'Saving…';
  try {
    status.value = await patchWorkerScheduler(patch);
    actionTone.value = status.value.blocked_by_env ? 'warn' : 'ok';
    actionMessage.value = status.value.blocked_by_env
      ? 'Saved — still blocked by AXON_WATCH_WORKER_SCHEDULER=0 in deployment.env'
      : 'Saved';
  } catch (error) {
    actionTone.value = 'error';
    actionMessage.value = error instanceof Error ? error.message : 'Save failed';
  } finally {
    saving.value = false;
  }
}

async function onToggleEnabled(event: Event): Promise<void> {
  const checked = (event.target as HTMLInputElement).checked;
  await persist({ scheduler_enabled: checked });
}

async function onMaxActiveChange(event: Event): Promise<void> {
  const value = Number((event.target as HTMLInputElement).value);
  if (!Number.isFinite(value)) {
    return;
  }
  await persist({ max_active: Math.max(1, Math.min(16, Math.round(value))) });
}

async function onStartsPerTickChange(event: Event): Promise<void> {
  const value = Number((event.target as HTMLInputElement).value);
  if (!Number.isFinite(value)) {
    return;
  }
  await persist({ max_starts_per_tick: Math.max(1, Math.min(8, Math.round(value))) });
}

function returnToTeamRoster(): void {
  if (shell.layoutMode !== 'ide') {
    shell.setLayoutMode('ide');
  }
  navigateToAppSurface('console');
  shell.setIdeActivityView('team');
}

async function onStopAll(): Promise<void> {
  stopping.value = true;
  actionTone.value = 'pending';
  actionMessage.value = 'Stopping active shifts…';
  try {
    status.value = await stopActiveWorkerRuns();
    const stopped = status.value.stopped_run_ids?.length ?? 0;
    const errors = status.value.stop_errors?.length ?? 0;
    actionTone.value = errors ? 'warn' : 'ok';
    actionMessage.value =
      errors > 0
        ? `Stopped ${stopped} shift(s); ${errors} could not stop`
        : `Stopped ${stopped} active shift(s)`;
  } catch (error) {
    actionTone.value = 'error';
    actionMessage.value = error instanceof Error ? error.message : 'Stop failed';
  } finally {
    stopping.value = false;
  }
}

onMounted(() => {
  void reload();
  refreshTimer = setInterval(() => {
    void reload();
  }, 8_000);
});

onUnmounted(() => {
  if (refreshTimer !== null) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
});
</script>

<template>
  <div class="agent-fleet-panel">
    <p class="agent-fleet-panel__back">
      <button type="button" class="agent-fleet-panel__back-link" @click="returnToTeamRoster">
        ← Team roster
      </button>
    </p>

    <p
      class="settings-feedback-banner settings-feedback-banner--inline"
      :class="{
        'settings-feedback-banner--error': actionTone === 'error',
        'settings-feedback-banner--ok': actionTone === 'ok',
        'settings-feedback-banner--pending': actionTone === 'pending',
        'settings-feedback-banner--warn': actionTone === 'warn',
      }"
      role="status"
      aria-live="polite"
    >
      {{
        actionMessage ||
        'Turn continuous workers on or off and cap how many can run at once — no env edits.'
      }}
    </p>

    <p v-if="loadState === 'loading' && !status" class="agent-fleet-panel__empty">Loading fleet…</p>

    <div
      v-else-if="loadState === 'error' && !status"
      class="agent-fleet-panel__load-error"
      role="alert"
    >
      <p>{{ actionMessage || 'Could not load agent fleet status.' }}</p>
      <button type="button" class="settings-surface__button settings-surface__primary" @click="reload">
        Try again
      </button>
    </div>

    <template v-else-if="status">
      <section class="operator-settings-form__section">
        <header class="operator-settings-form__section-header">
          <h2>Continuous workers</h2>
          <p>
            Master switch for always-on / continuous roster shifts. Caps keep memory under the
            control-plane MemoryHigh limit.
          </p>
        </header>

        <div class="agent-fleet-panel__toggles">
          <label class="agent-fleet-panel__toggle">
            <input
              type="checkbox"
              :checked="status.scheduler_enabled"
              :disabled="saving"
              @change="onToggleEnabled"
            />
            <span>Enable continuous workers</span>
          </label>
        </div>

        <dl class="operator-settings-form__status-grid">
          <div>
            <dt>Effective</dt>
            <dd>
              <span
                class="operator-settings-form__pill agent-fleet-panel__effective"
                :class="`agent-fleet-panel__effective--${effectiveTone}`"
              >
                {{ effectiveLabel }}
              </span>
            </dd>
          </div>
          <div>
            <dt>Executing now</dt>
            <dd>{{ status.executing_count }}</dd>
          </div>
          <div>
            <dt>Active runs</dt>
            <dd>{{ status.active_run_count }}</dd>
          </div>
          <div>
            <dt>Tick interval</dt>
            <dd>{{ status.tick_interval_seconds }}s</dd>
          </div>
        </dl>

        <p v-if="status.blocked_by_env" class="agent-fleet-panel__env-warn">
          Host emergency brake is on (<code>AXON_WATCH_WORKER_SCHEDULER=0</code>). Clear that in
          deployment.env, then reload — UI toggles will take effect.
        </p>
      </section>

      <section class="operator-settings-form__section">
        <header class="operator-settings-form__section-header">
          <h2>Concurrency caps</h2>
          <p>Lower these if Cursor and the desktop feel tight on RAM.</p>
        </header>

        <div class="agent-fleet-panel__caps">
          <label class="agent-fleet-panel__field">
            <span>Max active agents (1–16)</span>
            <input
              type="number"
              min="1"
              max="16"
              :value="status.max_active"
              :disabled="saving"
              @change="onMaxActiveChange"
            />
          </label>
          <label class="agent-fleet-panel__field">
            <span>Starts per tick (1–8)</span>
            <input
              type="number"
              min="1"
              max="8"
              :value="status.max_starts_per_tick"
              :disabled="saving"
              @change="onStartsPerTickChange"
            />
          </label>
        </div>
      </section>

      <section class="operator-settings-form__section">
        <header class="operator-settings-form__section-header">
          <h2>Emergency stop</h2>
          <p>Pause every non-terminal shift immediately. Does not change the master toggle.</p>
        </header>
        <div class="agent-fleet-panel__actions">
          <button
            type="button"
            class="settings-surface__button settings-surface__primary"
            :disabled="stopping || status.active_run_count === 0"
            @click="onStopAll"
          >
            {{ stopping ? 'Stopping…' : 'Stop all active shifts' }}
          </button>
          <button
            type="button"
            class="settings-surface__button"
            :disabled="saving"
            @click="reload"
          >
            Refresh
          </button>
        </div>
      </section>
    </template>
  </div>
</template>
