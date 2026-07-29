<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';

import {
  fetchAutonomyStatus,
  resolveAutonomyDecision,
  type AutonomyReceipt,
  type AutonomyStatusFeed,
} from '../../api/autonomy-api';
import { useWorkerAutonomyControl } from '../../composables/useWorkerAutonomyControl';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const {
  status,
  saving,
  killing,
  actionMessage,
  actionTone,
  autonomyMode,
  autonomousOn,
  readiness,
  effectiveLabel,
  effectiveTone,
  workersWantedOn,
  modeCopy,
  enableAutonomous,
  disableAutonomous,
  hardKill,
  reload,
} = useWorkerAutonomyControl({ pollMs: 8_000 });

const feed = ref<AutonomyStatusFeed | null>(null);
const confirmOpen = ref(false);
const feedError = ref<string | null>(null);
const feedUpdatedAt = ref<number | null>(null);
const resolvingId = ref<string | null>(null);
let feedTimer: ReturnType<typeof setInterval> | null = null;

const pendingCritical = computed<AutonomyReceipt[]>(() => {
  const workspaceId = shell.currentWorkspace?.workspace_id?.trim();
  return (feed.value?.pending_critical_decisions ?? []).filter(
    (item) => !workspaceId || !item.workspace_id || item.workspace_id === workspaceId,
  );
});
const pendingCriticalTotal = computed(
  () => feed.value?.pending_critical_count ?? pendingCritical.value.length,
);

const workerStateLabel = computed(() => {
  if (!status.value) {
    return 'Unknown';
  }
  if (status.value.blocked_by_env) {
    return 'Blocked';
  }
  if (autonomousOn.value && status.value.effective_enabled) {
    return 'Running';
  }
  if (autonomousOn.value) {
    return 'Configured · not effective';
  }
  return 'Paused';
});

async function reloadFeed(): Promise<void> {
  try {
    feed.value = await fetchAutonomyStatus(shell.currentWorkspace?.workspace_id);
    if (feed.value.autonomy_mode !== shell.operatorPresenceSettings.autonomy_mode) {
      await shell.loadOperatorPresenceSettings({ reportError: false });
    }
    feedUpdatedAt.value = Date.now();
    feedError.value = null;
  } catch (error) {
    feedError.value =
      error instanceof Error ? error.message : 'Autonomy status refresh failed';
  }
}

async function onToggleAutonomous(): Promise<void> {
  if (saving.value || killing.value) {
    return;
  }
  if (autonomousOn.value) {
    await disableAutonomous();
    await reloadFeed();
    return;
  }
  confirmOpen.value = true;
}

async function confirmEnable(): Promise<void> {
  confirmOpen.value = false;
  const ok = await enableAutonomous();
  if (ok) {
    await reloadFeed();
  }
}

function cancelConfirm(): void {
  confirmOpen.value = false;
}

async function onHardKill(): Promise<void> {
  await hardKill();
  await reloadFeed();
}

async function resolveDecision(
  item: AutonomyReceipt,
  resolution: 'approved' | 'rejected',
): Promise<void> {
  if (resolvingId.value) {
    return;
  }
  resolvingId.value = item.receipt_id;
  try {
    await resolveAutonomyDecision(item.receipt_id, resolution);
    await reloadFeed();
  } catch (error) {
    feedError.value =
      error instanceof Error ? error.message : 'Could not resolve autonomy decision';
  } finally {
    resolvingId.value = null;
  }
}

async function refreshAll(): Promise<void> {
  await Promise.all([reload(), reloadFeed()]);
}

function openAdvanced(): void {
  shell.openOperatorPresenceSettingsPanel();
}

onMounted(() => {
  void reloadFeed();
  feedTimer = setInterval(() => {
    void reloadFeed();
  }, 10_000);
});

onUnmounted(() => {
  if (feedTimer !== null) {
    clearInterval(feedTimer);
    feedTimer = null;
  }
});
</script>

<template>
  <section class="mc-autonomy" aria-label="VAXON autonomous control">
    <div class="mc-autonomy__row">
      <button
        type="button"
        class="mc-autonomy__toggle"
        :data-on="autonomousOn ? 'true' : 'false'"
        :disabled="saving || killing"
        :aria-pressed="autonomousOn"
        @click="void onToggleAutonomous()"
      >
        {{ autonomousOn ? 'AUTONOMOUS ON' : 'AUTONOMOUS OFF' }}
      </button>
      <span
        class="mc-autonomy__state"
        :data-tone="effectiveTone"
        role="status"
      >
        {{ workerStateLabel }}
      </span>
      <button
        type="button"
        class="mc-autonomy__kill"
        :disabled="killing || saving || (!workersWantedOn && (status?.active_run_count ?? 0) === 0)"
        title="Hard-kill continuous workers (demotes to Semi)"
        @click="void onHardKill()"
      >
        {{ killing ? 'Killing…' : 'Hard-kill' }}
      </button>
    </div>

    <p class="mc-autonomy__copy" role="note">
      {{ modeCopy[autonomyMode] }}
      <button type="button" class="mc-autonomy__link" @click="openAdvanced">
        Advanced
      </button>
    </p>

    <p
      v-if="actionMessage"
      class="mc-autonomy__banner"
      :data-tone="actionTone"
      role="status"
    >
      {{ actionMessage }}
    </p>

    <p v-if="feedError" class="mc-autonomy__banner" data-tone="error" role="alert">
      Status may be stale · {{ feedError }}
    </p>

    <p v-if="status?.blocked_by_env" class="mc-autonomy__warn" role="status">
      Host brake on (AXON_WATCH_WORKER_SCHEDULER=0). Full mode saves, but workers stay blocked.
    </p>

    <p v-if="readiness && readiness.grade !== 'ready'" class="mc-autonomy__warn" role="status">
      Readiness {{ readiness.score }}/100 ({{ readiness.grade }})
      <span v-if="readiness.blockers.length"> — {{ readiness.blockers[0] }}</span>
    </p>

    <div v-if="confirmOpen" class="mc-autonomy__confirm" role="dialog" aria-label="Confirm autonomous mode">
      <p>
        Turn AUTONOMOUS ON? VAXON will attend errors, warnings, and handoffs with isolated
        workers. Critical or dangerous actions still ask you.
      </p>
      <div class="mc-autonomy__confirm-actions">
        <button type="button" @click="cancelConfirm">Cancel</button>
        <button type="button" class="mc-autonomy__confirm-go" @click="void confirmEnable()">
          Enable
        </button>
      </div>
    </div>

    <ul v-if="pendingCritical.length" class="mc-autonomy__critical" aria-label="Needs your decision">
      <li v-for="item in pendingCritical.slice(0, 3)" :key="item.receipt_id">
        <strong>Needs you</strong>
        <span>{{ item.title || item.kind }}</span>
        <small v-if="item.detail">{{ item.detail }}</small>
        <small v-if="item.payload?.reason">Reason · {{ item.payload.reason }}</small>
        <div class="mc-autonomy__decision-actions">
          <button
            type="button"
            :disabled="Boolean(resolvingId)"
            @click="void resolveDecision(item, 'rejected')"
          >
            Reject
          </button>
          <button
            type="button"
            class="mc-autonomy__decision-approve"
            :disabled="Boolean(resolvingId)"
            @click="void resolveDecision(item, 'approved')"
          >
            {{ resolvingId === item.receipt_id ? 'Saving…' : 'Approve exact task' }}
          </button>
        </div>
      </li>
    </ul>
    <p v-if="pendingCriticalTotal > 3" class="mc-autonomy__warn">
      +{{ pendingCriticalTotal - 3 }} more decisions in this workspace
    </p>

    <div class="mc-autonomy__meta">
      <span>
        Mode · {{ autonomyMode }}
      </span>
      <span v-if="feed?.last_scan">
        Last scan
        <template v-if="feed.last_scan.scanned_at">
          · {{ new Date(feed.last_scan.scanned_at).toLocaleTimeString() }}
        </template>
        · dispatched {{ feed.last_scan.created_count ?? 0 }} · escalated
        {{ feed.last_scan.escalated_count ?? 0 }}
      </span>
      <span v-if="feedUpdatedAt">Feed refreshed · {{ new Date(feedUpdatedAt).toLocaleTimeString() }}</span>
      <button type="button" class="mc-autonomy__link" @click="void refreshAll()">
        Refresh
      </button>
    </div>
  </section>
</template>

<style scoped>
.mc-autonomy {
  display: grid;
  gap: 0.45rem;
  padding: 0.55rem 0.65rem;
  border-top: 1px solid color-mix(in srgb, var(--hud-cyan, #5ee7ff) 18%, transparent);
  background: color-mix(in srgb, #041018 72%, transparent);
}

.mc-autonomy__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem;
}

.mc-autonomy__toggle {
  border: 1px solid color-mix(in srgb, var(--hud-cyan, #5ee7ff) 45%, transparent);
  background: color-mix(in srgb, #0b2430 80%, transparent);
  color: #d7f7ff;
  font: 650 0.68rem/1 ui-monospace, SFMono-Regular, Menlo, monospace;
  letter-spacing: 0.08em;
  padding: 0.35rem 0.55rem;
  cursor: pointer;
}

.mc-autonomy__toggle[data-on='true'] {
  border-color: color-mix(in srgb, #3dff9a 55%, transparent);
  background: color-mix(in srgb, #0d3a28 75%, transparent);
  color: #c8ffe0;
}

.mc-autonomy__state {
  font: 600 0.65rem/1 ui-monospace, SFMono-Regular, Menlo, monospace;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #9ec9d6;
}

.mc-autonomy__state[data-tone='running'] {
  color: #7dffb2;
}

.mc-autonomy__state[data-tone='blocked'],
.mc-autonomy__state[data-tone='paused'] {
  color: #ffd27a;
}

.mc-autonomy__kill {
  margin-left: auto;
  border: 1px solid color-mix(in srgb, #ff6b6b 50%, transparent);
  background: color-mix(in srgb, #3a1010 70%, transparent);
  color: #ffd0d0;
  font: 600 0.62rem/1 ui-monospace, SFMono-Regular, Menlo, monospace;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  padding: 0.3rem 0.45rem;
  cursor: pointer;
}

.mc-autonomy__kill:disabled,
.mc-autonomy__toggle:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.mc-autonomy__copy,
.mc-autonomy__meta,
.mc-autonomy__banner,
.mc-autonomy__warn {
  margin: 0;
  font: 0.68rem/1.35 system-ui, sans-serif;
  color: #9eb8c4;
}

.mc-autonomy__banner[data-tone='ok'] {
  color: #8dffb8;
}

.mc-autonomy__banner[data-tone='error'] {
  color: #ff9a9a;
}

.mc-autonomy__banner[data-tone='warn'],
.mc-autonomy__warn {
  color: #ffd27a;
}

.mc-autonomy__link {
  border: 0;
  background: transparent;
  color: #7fd7ff;
  font: inherit;
  text-decoration: underline;
  cursor: pointer;
  padding: 0;
  margin-left: 0.35rem;
}

.mc-autonomy__confirm {
  display: grid;
  gap: 0.4rem;
  padding: 0.5rem;
  border: 1px solid color-mix(in srgb, #ffd27a 40%, transparent);
  background: color-mix(in srgb, #2a2108 70%, transparent);
}

.mc-autonomy__confirm p {
  margin: 0;
  font: 0.7rem/1.35 system-ui, sans-serif;
  color: #ffe7b0;
}

.mc-autonomy__confirm-actions {
  display: flex;
  gap: 0.4rem;
  justify-content: flex-end;
}

.mc-autonomy__confirm-actions button {
  border: 1px solid color-mix(in srgb, #9ec9d6 35%, transparent);
  background: transparent;
  color: #d7f7ff;
  font: 0.65rem/1 system-ui, sans-serif;
  padding: 0.28rem 0.45rem;
  cursor: pointer;
}

.mc-autonomy__confirm-go {
  border-color: color-mix(in srgb, #3dff9a 55%, transparent) !important;
  background: color-mix(in srgb, #0d3a28 75%, transparent) !important;
}

.mc-autonomy__critical {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.3rem;
}

.mc-autonomy__critical li {
  display: grid;
  gap: 0.1rem;
  padding: 0.35rem 0.45rem;
  border: 1px solid color-mix(in srgb, #ff6b6b 35%, transparent);
  background: color-mix(in srgb, #2a1010 65%, transparent);
  font: 0.66rem/1.3 system-ui, sans-serif;
  color: #ffd0d0;
}

.mc-autonomy__critical strong {
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-size: 0.58rem;
  color: #ff9a9a;
}

.mc-autonomy__critical small {
  color: #e7bcbc;
  overflow-wrap: anywhere;
}

.mc-autonomy__decision-actions {
  display: flex;
  gap: 0.35rem;
  justify-content: flex-end;
  margin-top: 0.2rem;
}

.mc-autonomy__decision-actions button {
  border: 1px solid color-mix(in srgb, #ff9a9a 45%, transparent);
  background: transparent;
  color: #ffd0d0;
  font: 0.62rem/1 system-ui, sans-serif;
  padding: 0.3rem 0.4rem;
  cursor: pointer;
}

.mc-autonomy__decision-approve {
  border-color: color-mix(in srgb, #ffd27a 50%, transparent) !important;
  color: #ffe7b0 !important;
}

.mc-autonomy__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  align-items: center;
}
</style>
