import { computed, onMounted, onUnmounted, ref, type Ref } from 'vue';

import {
  fetchWorkerSchedulerStatus,
  hardKillWorkerScheduler,
  resumeWorkerScheduler,
  stopActiveWorkerRuns,
  type WorkerSchedulerStatus,
} from '../api/worker-scheduler-api';
import type { AutonomyMode } from '../contracts/canonical';
import { useShellStore } from '../stores/shell';

export type AutonomyActionTone = 'idle' | 'ok' | 'error' | 'pending' | 'warn';

export const AUTONOMY_MODE_COPY: Record<AutonomyMode, string> = {
  manual:
    'VAXON speaks only for approvals and interruptive signals. Continuous workers stay paused. The monitoring lane can still watch for blockers and bugs.',
  semi:
    'VAXON stays proactive with advisory briefs. Continuous workers stay paused (no idle Cursor burn). The monitoring lane keeps observing; Full is required for always-on leasing.',
  full:
    'VAXON advisory plus continuous workers that lease tasks and run Cursor shifts without per-run approval. Monitoring remains separate and always-on unless explicitly braked.',
};

export function useWorkerAutonomyControl(options?: {
  pollMs?: number;
  autoLoad?: boolean;
}) {
  const shell = useShellStore();
  const status = ref<WorkerSchedulerStatus | null>(null);
  const loadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('idle');
  const saving = ref(false);
  const stopping = ref(false);
  const killing = ref(false);
  const resuming = ref(false);
  const actionMessage = ref<string | null>(null);
  const actionTone = ref<AutonomyActionTone>('idle');
  let refreshTimer: ReturnType<typeof setInterval> | null = null;

  const autonomyMode = computed<AutonomyMode>(
    () => shell.operatorPresenceSettings.autonomy_mode ?? 'manual',
  );
  const autonomousOn = computed(() => autonomyMode.value === 'full');
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
  const watcherLabel = computed(() => {
    if (!status.value) {
      return 'Unknown';
    }
    if (status.value.watcher_blocked_by_env) {
      return 'Blocked by host brake';
    }
    return status.value.watcher_effective_enabled ? 'Watching' : 'Paused';
  });
  const watcherTone = computed(() => {
    if (!status.value) {
      return 'unknown';
    }
    if (status.value.watcher_blocked_by_env) {
      return 'blocked';
    }
    return status.value.watcher_effective_enabled ? 'running' : 'paused';
  });

  async function reload(): Promise<void> {
    loadState.value = status.value ? loadState.value : 'loading';
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

  async function setAutonomyMode(mode: AutonomyMode): Promise<boolean> {
    if (mode === autonomyMode.value || saving.value) {
      return false;
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
      return true;
    } catch (error) {
      actionTone.value = 'error';
      actionMessage.value =
        error instanceof Error ? error.message : 'Could not save autonomy mode';
      return false;
    } finally {
      saving.value = false;
    }
  }

  async function enableAutonomous(): Promise<boolean> {
    // AUTO ON = VAXON CEO mode: Full autonomy + workers unpaused (unless env-blocked).
    // If already Full, still resume — screenshot trap was AUTO ON with Workers paused.
    if (autonomyMode.value !== 'full') {
      const modeOk = await setAutonomyMode('full');
      if (!modeOk) {
        return false;
      }
    }
    let resumed = true;
    if (!status.value?.effective_enabled) {
      resumed = await resume();
    }
    return resumed;
  }

  async function disableAutonomous(): Promise<boolean> {
    // OFF is an operational stop, not only a future-start toggle.
    return hardKill();
  }

  async function hardKill(): Promise<boolean> {
    killing.value = true;
    actionTone.value = 'pending';
    actionMessage.value = 'Hard-killing continuous workers…';
    try {
      status.value = await hardKillWorkerScheduler();
      await shell.loadOperatorPresenceSettings({ reportError: false });
      const stopped = status.value.stopped_run_ids?.length ?? 0;
      const errors = status.value.stop_errors?.length ?? 0;
      actionTone.value = errors > 0 ? 'warn' : 'ok';
      actionMessage.value = errors
        ? `Scheduler paused and demoted to Semi — ${stopped} shift(s) stopped; ${errors} could not stop. Review active runs.`
        : `Scheduler hard-killed — ${stopped} shift(s) stopped. VAXON stays on Semi (proactive).`;
      return true;
    } catch (error) {
      actionTone.value = 'error';
      actionMessage.value =
        error instanceof Error ? error.message : 'Hard-kill failed';
      return false;
    } finally {
      killing.value = false;
    }
  }

  async function resume(): Promise<boolean> {
    resuming.value = true;
    actionTone.value = 'pending';
    actionMessage.value = 'Resuming continuous workers…';
    try {
      status.value = await resumeWorkerScheduler();
      await shell.loadOperatorPresenceSettings({ reportError: false });
      if (status.value.blocked_by_env) {
        actionTone.value = 'warn';
        actionMessage.value =
          'Resume saved — host brake still on (AXON_WATCH_WORKER_SCHEDULER=0).';
      } else if (status.value.effective_enabled) {
        actionTone.value = 'ok';
        actionMessage.value =
          'Continuous workers resumed. Full autonomy on — Cursor usage only when a leased task dispatches.';
      } else {
        actionTone.value = 'warn';
        actionMessage.value = 'Resume saved but workers are not effective yet.';
      }
      return true;
    } catch (error) {
      actionTone.value = 'error';
      actionMessage.value =
        error instanceof Error ? error.message : 'Resume failed';
      return false;
    } finally {
      resuming.value = false;
    }
  }

  async function stopActive(): Promise<boolean> {
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
      return true;
    } catch (error) {
      actionTone.value = 'error';
      actionMessage.value = error instanceof Error ? error.message : 'Stop failed';
      return false;
    } finally {
      stopping.value = false;
    }
  }

  function startPolling(): void {
    if (refreshTimer !== null) {
      return;
    }
    const ms = Math.max(4_000, options?.pollMs ?? 8_000);
    refreshTimer = setInterval(() => {
      void reload();
    }, ms);
  }

  function stopPolling(): void {
    if (refreshTimer !== null) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  }

  if (options?.autoLoad !== false) {
    onMounted(() => {
      void shell.loadOperatorPresenceSettings({ reportError: false });
      void reload();
      startPolling();
    });
    onUnmounted(() => {
      stopPolling();
    });
  }

  return {
    status: status as Ref<WorkerSchedulerStatus | null>,
    loadState,
    saving,
    stopping,
    killing,
    resuming,
    actionMessage,
    actionTone,
    autonomyMode,
    autonomousOn,
    readiness,
    effectiveLabel,
    effectiveTone,
    workersWantedOn,
    watcherLabel,
    watcherTone,
    modeCopy: AUTONOMY_MODE_COPY,
    reload,
    setAutonomyMode,
    enableAutonomous,
    disableAutonomous,
    hardKill,
    resume,
    stopActive,
    startPolling,
    stopPolling,
  };
}
