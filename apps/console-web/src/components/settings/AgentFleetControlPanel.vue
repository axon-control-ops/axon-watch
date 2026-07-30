<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';

import {
  fetchWorkerSchedulerStatus,
  hardKillWorkerScheduler,
  patchWorkerScheduler,
  resumeWorkerScheduler,
  stopActiveWorkerRuns,
  type WorkerSchedulerStatus,
} from '../../api/worker-scheduler-api';
import type { AutonomyMode } from '../../contracts/canonical';
import { navigateToAppSurface } from '../../lib/app-surface-route';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const status = ref<WorkerSchedulerStatus | null>(null);
const loadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('idle');
const saving = ref(false);
const stopping = ref(false);
const killing = ref(false);
const resuming = ref(false);
const actionMessage = ref<string | null>(null);
const actionTone = ref<'idle' | 'ok' | 'error' | 'pending' | 'warn'>('idle');
let refreshTimer: ReturnType<typeof setInterval> | null = null;

const autonomyMode = computed<AutonomyMode>(
  () => shell.operatorPresenceSettings.autonomy_mode ?? 'manual',
);

const readiness = computed(() => shell.operatorBriefing?.production_readiness ?? null);

const effectiveLabel = computed(() => {
  if (!status.value) {
    return 'Unknown';
  }
  if (status.value.blocked_by_env) {
    return 'Blocked by host brake';
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

const workersWantedOn = computed(() => Boolean(status.value?.scheduler_enabled));

const modeCopy: Record<AutonomyMode, string> = {
  manual:
    'VAXON speaks only for approvals and interruptive signals. Continuous workers stay paused. Lead Send still kicks specialists for that handoff.',
  semi:
    'VAXON stays proactive with advisory briefs. Continuous workers stay paused (no idle Cursor burn). Lead Send still kicks specialists for that handoff — Full is required for always-on leasing.',
  full:
    'VAXON advisory plus continuous workers that lease tasks and run Cursor shifts without per-run approval.',
};

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

async function persistCaps(patch: {
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
    await shell.loadOperatorPresenceSettings({ reportError: false });
  } catch (error) {
    actionTone.value = 'error';
    actionMessage.value = error instanceof Error ? error.message : 'Save failed';
  } finally {
    saving.value = false;
  }
}

async function onAutonomyModeChange(mode: AutonomyMode): Promise<void> {
  if (mode === autonomyMode.value || saving.value) {
    return;
  }
  saving.value = true;
  actionTone.value = 'pending';
  actionMessage.value = 'Saving autonomy mode…';
  try {
    await shell.saveOperatorPresenceSettingsPatch({ autonomy_mode: mode });
    status.value = await fetchWorkerSchedulerStatus();
    actionTone.value = status.value.blocked_by_env && mode === 'full' ? 'warn' : 'ok';
    actionMessage.value =
      status.value.blocked_by_env && mode === 'full'
        ? 'Full autonomy saved — workers still blocked by AXON_WATCH_WORKER_SCHEDULER=0'
        : mode === 'semi'
          ? 'Semi-autonomous — VAXON stays proactive; continuous workers paused'
          : mode === 'manual'
            ? 'Manual — VAXON quiet except approvals; workers paused'
            : 'Full autonomous — continuous workers will start leased tasks';
  } catch (error) {
    actionTone.value = 'error';
    actionMessage.value =
      error instanceof Error ? error.message : 'Could not save autonomy mode';
  } finally {
    saving.value = false;
  }
}

async function onMaxActiveChange(event: Event): Promise<void> {
  const value = Number((event.target as HTMLInputElement).value);
  if (!Number.isFinite(value)) {
    return;
  }
  await persistCaps({ max_active: Math.max(1, Math.min(16, Math.round(value))) });
}

async function onStartsPerTickChange(event: Event): Promise<void> {
  const value = Number((event.target as HTMLInputElement).value);
  if (!Number.isFinite(value)) {
    return;
  }
  await persistCaps({ max_starts_per_tick: Math.max(1, Math.min(8, Math.round(value))) });
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

async function onHardKill(): Promise<void> {
  killing.value = true;
  actionTone.value = 'pending';
  actionMessage.value = 'Hard-killing continuous workers…';
  try {
    status.value = await hardKillWorkerScheduler();
    await shell.loadOperatorPresenceSettings({ reportError: false });
    const stopped = status.value.stopped_run_ids?.length ?? 0;
    actionTone.value = 'ok';
    actionMessage.value =
      `Scheduler hard-killed from Settings — ${stopped} shift(s) stopped. ` +
      'VAXON stays on Semi (proactive). Resume anytime without editing .env.';
  } catch (error) {
    actionTone.value = 'error';
    actionMessage.value =
      error instanceof Error ? error.message : 'Hard-kill failed';
  } finally {
    killing.value = false;
  }
}

async function onResume(): Promise<void> {
  resuming.value = true;
  actionTone.value = 'pending';
  actionMessage.value = 'Resuming continuous workers…';
  try {
    status.value = await resumeWorkerScheduler();
    await shell.loadOperatorPresenceSettings({ reportError: false });
    if (status.value.blocked_by_env) {
      actionTone.value = 'warn';
      actionMessage.value =
        'Settings resume saved — host brake still on (AXON_WATCH_WORKER_SCHEDULER=0). Clear that in deployment.env to actually start workers.';
    } else if (status.value.effective_enabled) {
      actionTone.value = 'ok';
      actionMessage.value =
        'Continuous workers resumed. Full autonomy on — Cursor usage only when a leased task dispatches.';
    } else {
      actionTone.value = 'warn';
      actionMessage.value = 'Resume saved but workers are not effective yet — refresh and check status.';
    }
  } catch (error) {
    actionTone.value = 'error';
    actionMessage.value =
      error instanceof Error ? error.message : 'Resume failed';
  } finally {
    resuming.value = false;
  }
}

onMounted(() => {
  void shell.loadOperatorPresenceSettings({ reportError: false });
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
        'Semi keeps VAXON proactive with workers off. Full starts continuous Cursor shifts. Hard-kill and resume live here — no .env edit for day-to-day control.'
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
          <h2>VAXON autonomy</h2>
          <p>{{ modeCopy[autonomyMode] }}</p>
        </header>

        <div class="agent-fleet-panel__modes" role="radiogroup" aria-label="Autonomy mode">
          <label
            v-for="mode in (['manual', 'semi', 'full'] as const)"
            :key="mode"
            class="agent-fleet-panel__mode"
            :class="{ 'agent-fleet-panel__mode--active': autonomyMode === mode }"
          >
            <input
              type="radio"
              name="autonomy-mode"
              :value="mode"
              :checked="autonomyMode === mode"
              :disabled="saving || killing || resuming"
              @change="onAutonomyModeChange(mode)"
            />
            <span class="agent-fleet-panel__mode-copy">
              <span class="agent-fleet-panel__mode-label">
                {{ mode === 'manual' ? 'Manual' : mode === 'semi' ? 'Semi-autonomous' : 'Full autonomous' }}
              </span>
              <span class="agent-fleet-panel__mode-meta">
                {{
                  mode === 'manual'
                    ? 'Quiet VAXON · workers off'
                    : mode === 'semi'
                      ? 'Proactive VAXON · workers off'
                      : 'Proactive VAXON · workers on'
                }}
              </span>
            </span>
          </label>
        </div>
      </section>

      <section class="operator-settings-form__section">
        <header class="operator-settings-form__section-header">
          <h2>Continuous worker scheduler</h2>
          <p>
            Hard-kill pauses new starts and stops active shifts from Settings (SQLite). Resume re-enables
            without touching deployment.env — unless the host emergency brake is on.
          </p>
        </header>

        <dl class="operator-settings-form__status-grid">
          <div>
            <dt>Workers</dt>
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
            <dt>Settings switch</dt>
            <dd>{{ workersWantedOn ? 'On' : 'Off' }}</dd>
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
          <div>
            <dt>Cursor on idle</dt>
            <dd>{{ status.cursor_usage_on_idle_tick ? 'Yes' : 'No' }}</dd>
          </div>
        </dl>

        <p class="agent-fleet-panel__usage-note" role="note">
          Idle scheduler ticks do not call Cursor CLI. Usage only when a leased task actually
          dispatches a worker shift.
        </p>

        <p v-if="readiness" class="agent-fleet-panel__readiness" role="status">
          Production readiness
          <strong>{{ readiness.score }}/100</strong>
          ({{ readiness.grade }})
          <span v-if="readiness.blockers.length"> — {{ readiness.blockers[0] }}</span>
        </p>

        <p v-if="status.blocked_by_env" class="agent-fleet-panel__env-warn">
          Host emergency brake is on (<code>AXON_WATCH_WORKER_SCHEDULER=0</code>). Settings resume
          will save the SQLite switch, but workers stay blocked until that env flag is cleared and
          the control plane reloads.
        </p>

        <div class="agent-fleet-panel__actions agent-fleet-panel__actions--scheduler">
          <button
            type="button"
            class="settings-surface__button agent-fleet-panel__kill"
            :disabled="killing || resuming || saving || (!workersWantedOn && status.active_run_count === 0)"
            @click="onHardKill"
          >
            {{ killing ? 'Hard-killing…' : 'Hard-kill scheduler' }}
          </button>
          <button
            type="button"
            class="settings-surface__button settings-surface__primary"
            :disabled="resuming || killing || saving || (workersWantedOn && status.effective_enabled)"
            @click="onResume"
          >
            {{ resuming ? 'Resuming…' : 'Resume scheduler' }}
          </button>
          <button
            type="button"
            class="settings-surface__button"
            :disabled="saving || killing || resuming"
            @click="reload"
          >
            Refresh
          </button>
        </div>
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
              :disabled="saving || killing || resuming"
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
              :disabled="saving || killing || resuming"
              @change="onStartsPerTickChange"
            />
          </label>
        </div>
      </section>

      <section class="operator-settings-form__section">
        <header class="operator-settings-form__section-header">
          <h2>Stop active shifts only</h2>
          <p>
            Pause every non-terminal worker shift immediately. Does not change the scheduler switch
            or autonomy mode — use Hard-kill to pause starts and keep VAXON on Semi.
          </p>
        </header>
        <div class="agent-fleet-panel__actions">
          <button
            type="button"
            class="settings-surface__button settings-surface__primary"
            :disabled="stopping || status.active_run_count === 0 || killing || resuming"
            @click="onStopAll"
          >
            {{ stopping ? 'Stopping…' : 'Stop all active shifts' }}
          </button>
        </div>
      </section>
    </template>
  </div>
</template>
