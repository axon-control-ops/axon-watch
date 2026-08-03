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
  effectiveTone,
  workersWantedOn,
  enableAutonomous,
  disableAutonomous,
  hardKill,
  reload,
} = useWorkerAutonomyControl({ pollMs: 8_000 });

const feed = ref<AutonomyStatusFeed | null>(null);
const confirmOpen = ref(false);
const feedError = ref<string | null>(null);
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
    return 'Armed';
  }
  return 'Paused';
});

const telemetryLine = computed(() => {
  const parts = [workerStateLabel.value, autonomyMode.value];
  const scan = feed.value?.last_scan;
  if (scan) {
    parts.push(`+${scan.created_count ?? 0}`);
    if ((scan.escalated_count ?? 0) > 0) {
      parts.push(`↑${scan.escalated_count}`);
    }
  }
  if (readiness.value && readiness.value.grade !== 'ready') {
    parts.push(`${readiness.value.score}/100`);
  }
  return parts.join(' · ');
});

const showAlert = computed(
  () =>
    Boolean(actionMessage.value) ||
    Boolean(feedError.value) ||
    Boolean(status.value?.blocked_by_env) ||
    Boolean(readiness.value && readiness.value.grade !== 'ready'),
);

async function reloadFeed(): Promise<void> {
  try {
    feed.value = await fetchAutonomyStatus(shell.currentWorkspace?.workspace_id);
    if (feed.value.autonomy_mode !== shell.operatorPresenceSettings.autonomy_mode) {
      await shell.loadOperatorPresenceSettings({ reportError: false });
    }
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
  <section
    class="orb-hud"
    :data-tone="effectiveTone"
    :data-armed="autonomousOn ? 'true' : 'false'"
    aria-label="VAXON orb controls"
  >
    <div class="orb-hud__glow" aria-hidden="true" />
    <div class="orb-hud__arc" aria-hidden="true" />

    <div class="orb-hud__ring">
      <button
        type="button"
        class="orb-hud__chip orb-hud__chip--prime"
        :data-on="autonomousOn ? 'true' : 'false'"
        :disabled="saving || killing"
        :aria-pressed="autonomousOn"
        :title="autonomousOn ? 'Turn autonomous off' : 'Turn autonomous on'"
        @click="void onToggleAutonomous()"
      >
        <span class="orb-hud__chip-dot" aria-hidden="true" />
        {{ autonomousOn ? 'AUTO ON' : 'AUTO OFF' }}
      </button>

      <button
        type="button"
        class="orb-hud__chip orb-hud__chip--kill"
        :disabled="killing || saving || (!workersWantedOn && (status?.active_run_count ?? 0) === 0)"
        title="Hard-kill continuous workers"
        @click="void onHardKill()"
      >
        {{ killing ? '…' : 'KILL' }}
      </button>

      <button
        type="button"
        class="orb-hud__chip"
        title="Advanced autonomy settings"
        @click="openAdvanced"
      >
        ADV
      </button>

      <button
        type="button"
        class="orb-hud__chip orb-hud__chip--icon"
        title="Refresh autonomy status"
        @click="void refreshAll()"
      >
        ↻
      </button>
    </div>

    <p class="orb-hud__telemetry" role="status">
      <span class="orb-hud__telemetry-pulse" :data-tone="effectiveTone" aria-hidden="true" />
      <span>{{ telemetryLine }}</span>
    </p>

    <p
      v-if="showAlert && actionMessage"
      class="orb-hud__whisper"
      :data-tone="actionTone"
      role="status"
    >
      {{ actionMessage }}
    </p>
    <p v-else-if="feedError" class="orb-hud__whisper" data-tone="error" role="alert">
      {{ feedError }}
    </p>
    <p v-else-if="status?.blocked_by_env" class="orb-hud__whisper" data-tone="warn" role="status">
      Host brake on
    </p>

    <div
      v-if="confirmOpen"
      class="orb-hud__sheet"
      role="dialog"
      aria-label="Confirm autonomous mode"
    >
      <p>Enable full autonomy? Critical actions still ask you.</p>
      <div class="orb-hud__sheet-actions">
        <button type="button" @click="cancelConfirm">Cancel</button>
        <button type="button" class="orb-hud__sheet-go" @click="void confirmEnable()">
          Enable
        </button>
      </div>
    </div>

    <div v-if="pendingCritical.length" class="orb-hud__sheet orb-hud__sheet--critical">
      <ul aria-label="Needs your decision">
        <li v-for="item in pendingCritical.slice(0, 2)" :key="item.receipt_id">
          <strong>Needs you</strong>
          <span>{{ item.title || item.kind }}</span>
          <div class="orb-hud__sheet-actions">
            <button
              type="button"
              :disabled="Boolean(resolvingId)"
              @click="void resolveDecision(item, 'rejected')"
            >
              Reject
            </button>
            <button
              type="button"
              class="orb-hud__sheet-go"
              :disabled="Boolean(resolvingId)"
              @click="void resolveDecision(item, 'approved')"
            >
              {{ resolvingId === item.receipt_id ? '…' : 'Approve' }}
            </button>
          </div>
        </li>
      </ul>
      <p v-if="pendingCriticalTotal > 2" class="orb-hud__whisper" data-tone="warn">
        +{{ pendingCriticalTotal - 2 }} more
      </p>
    </div>
  </section>
</template>

<style scoped>
.orb-hud {
  --orb-hud-cyan: rgba(110, 235, 255, 0.95);
  --orb-hud-ink: rgba(2, 10, 18, 0.2);
  position: absolute;
  left: 0.35rem;
  right: 0.35rem;
  bottom: 0.35rem;
  z-index: 4;
  display: grid;
  justify-items: center;
  gap: 0.28rem;
  padding: 0.85rem 0.35rem 0.2rem;
  pointer-events: none;
  isolation: isolate;
}

.orb-hud__glow {
  position: absolute;
  inset: auto 0 0 0;
  height: 4.2rem;
  background:
    radial-gradient(ellipse 85% 90% at 50% 100%, rgba(0, 180, 255, 0.16), transparent 72%),
    linear-gradient(180deg, transparent, rgba(1, 8, 16, 0.28));
  pointer-events: none;
  z-index: 0;
  border-radius: 0 0 0.7rem 0.7rem;
}

.orb-hud[data-armed='true'] .orb-hud__glow {
  background:
    radial-gradient(ellipse 85% 90% at 50% 100%, rgba(40, 255, 170, 0.14), transparent 72%),
    linear-gradient(180deg, transparent, rgba(1, 12, 14, 0.22));
}

.orb-hud__arc {
  display: none;
}

.orb-hud[data-armed='true'] .orb-hud__arc {
  border-color: rgba(90, 255, 190, 0.35);
  box-shadow:
    0 -0.35rem 1.2rem rgba(40, 255, 170, 0.14),
    inset 0 1px 0 rgba(180, 255, 220, 0.2);
}

.orb-hud__arc::after {
  content: '';
  position: absolute;
  left: 8%;
  right: 8%;
  top: -1px;
  height: 2px;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(120, 240, 255, 0.15),
    rgba(180, 250, 255, 0.95),
    rgba(120, 240, 255, 0.15),
    transparent
  );
  animation: orb-hud-scan 2.8s linear infinite;
}

.orb-hud__ring {
  position: relative;
  z-index: 2;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  gap: 0.35rem;
  pointer-events: auto;
}

.orb-hud__chip {
  position: relative;
  appearance: none;
  border: 1px solid rgba(110, 220, 255, 0.42);
  border-radius: 999px;
  padding: 0.32rem 0.65rem;
  color: rgba(210, 245, 255, 0.94);
  background: rgba(4, 18, 28, 0.42);
  box-shadow:
    inset 0 0 0 1px rgba(140, 235, 255, 0.1),
    0 0 0.65rem rgba(0, 180, 255, 0.14);
  backdrop-filter: blur(8px);
  font: 650 0.56rem/1 var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  cursor: pointer;
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease,
    color 160ms ease,
    transform 160ms ease,
    background 160ms ease;
}

.orb-hud__chip:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(140, 240, 255, 0.72);
  box-shadow:
    inset 0 0 0 1px rgba(160, 245, 255, 0.16),
    0 0 1rem rgba(0, 220, 255, 0.28);
  color: rgba(235, 252, 255, 0.98);
}

.orb-hud__chip:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.orb-hud__chip--prime {
  padding-left: 0.55rem;
  min-width: 5.6rem;
}

.orb-hud__chip--prime .orb-hud__chip-dot {
  display: inline-block;
  width: 0.35rem;
  height: 0.35rem;
  margin-right: 0.35rem;
  border-radius: 50%;
  background: rgba(160, 200, 220, 0.55);
  box-shadow: 0 0 0.35rem rgba(120, 200, 230, 0.35);
  vertical-align: 0.02rem;
}

.orb-hud__chip--prime[data-on='true'] {
  border-color: rgba(90, 255, 190, 0.65);
  color: rgba(210, 255, 235, 0.98);
  background:
    linear-gradient(180deg, rgba(20, 80, 55, 0.45), rgba(4, 28, 18, 0.55)),
    rgba(4, 28, 18, 0.4);
  box-shadow:
    inset 0 0 0 1px rgba(140, 255, 210, 0.14),
    0 0 1.1rem rgba(40, 255, 170, 0.28);
  animation: orb-hud-armed 2.4s ease-in-out infinite;
}

.orb-hud__chip--prime[data-on='true'] .orb-hud__chip-dot {
  background: rgba(90, 255, 190, 0.95);
  box-shadow: 0 0 0.55rem rgba(70, 255, 180, 0.75);
}

.orb-hud__chip--kill {
  border-color: rgba(255, 120, 140, 0.45);
  color: rgba(255, 210, 220, 0.95);
  background:
    linear-gradient(180deg, rgba(70, 18, 28, 0.4), rgba(28, 8, 12, 0.5)),
    rgba(28, 8, 12, 0.35);
  box-shadow:
    inset 0 0 0 1px rgba(255, 140, 160, 0.1),
    0 0 0.7rem rgba(255, 70, 100, 0.12);
}

.orb-hud__chip--kill:hover:not(:disabled) {
  border-color: rgba(255, 140, 160, 0.8);
  box-shadow:
    inset 0 0 0 1px rgba(255, 160, 180, 0.18),
    0 0 1rem rgba(255, 80, 110, 0.28);
}

.orb-hud__chip--icon {
  min-width: 1.9rem;
  padding-left: 0.45rem;
  padding-right: 0.45rem;
  letter-spacing: 0;
}

.orb-hud__telemetry {
  position: relative;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0;
  max-width: 100%;
  padding: 0.12rem 0.55rem;
  color: rgba(160, 215, 235, 0.82);
  font: 0.52rem/1.2 var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  text-shadow: 0 0 0.55rem rgba(0, 200, 255, 0.25);
  pointer-events: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.orb-hud__telemetry-pulse {
  width: 0.35rem;
  height: 0.35rem;
  border-radius: 50%;
  background: rgba(140, 200, 220, 0.7);
  box-shadow: 0 0 0.4rem rgba(100, 210, 255, 0.45);
  flex: 0 0 auto;
}

.orb-hud__telemetry-pulse[data-tone='running'] {
  background: rgba(90, 255, 190, 0.95);
  box-shadow: 0 0 0.55rem rgba(70, 255, 180, 0.7);
  animation: orb-hud-pulse 1.4s ease-in-out infinite;
}

.orb-hud__telemetry-pulse[data-tone='paused'],
.orb-hud__telemetry-pulse[data-tone='blocked'] {
  background: rgba(255, 210, 120, 0.9);
  box-shadow: 0 0 0.45rem rgba(255, 190, 90, 0.45);
}

.orb-hud__whisper {
  position: relative;
  z-index: 2;
  margin: 0;
  max-width: 92%;
  text-align: center;
  color: rgba(170, 210, 225, 0.85);
  font: 0.55rem/1.25 system-ui, sans-serif;
  pointer-events: none;
}

.orb-hud__whisper[data-tone='ok'] {
  color: rgba(150, 255, 200, 0.92);
}

.orb-hud__whisper[data-tone='error'] {
  color: rgba(255, 160, 170, 0.95);
}

.orb-hud__whisper[data-tone='warn'],
.orb-hud__whisper[data-tone='pending'] {
  color: rgba(255, 210, 140, 0.95);
}

.orb-hud__sheet {
  position: relative;
  z-index: 3;
  width: min(100%, 18rem);
  display: grid;
  gap: 0.4rem;
  margin-top: 0.1rem;
  padding: 0.55rem 0.6rem;
  border: 1px solid rgba(255, 210, 120, 0.35);
  border-radius: 0.65rem;
  background:
    linear-gradient(180deg, rgba(40, 30, 8, 0.55), rgba(12, 10, 4, 0.72)),
    rgba(8, 8, 4, 0.55);
  box-shadow:
    0 0 1.4rem rgba(0, 0, 0, 0.35),
    inset 0 0 0 1px rgba(255, 230, 160, 0.08);
  backdrop-filter: blur(12px);
  pointer-events: auto;
  animation: orb-hud-sheet-in 180ms ease-out;
}

.orb-hud__sheet--critical {
  border-color: rgba(255, 120, 140, 0.4);
  background:
    linear-gradient(180deg, rgba(50, 12, 18, 0.55), rgba(16, 4, 8, 0.72)),
    rgba(16, 4, 8, 0.55);
  max-height: 6.5rem;
  overflow: auto;
  overscroll-behavior: contain;
}

.orb-hud__sheet p,
.orb-hud__sheet span {
  margin: 0;
  color: rgba(255, 235, 200, 0.95);
  font: 0.62rem/1.3 system-ui, sans-serif;
}

.orb-hud__sheet ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.35rem;
}

.orb-hud__sheet li {
  display: grid;
  gap: 0.15rem;
  color: rgba(255, 220, 225, 0.95);
  font: 0.6rem/1.25 system-ui, sans-serif;
}

.orb-hud__sheet strong {
  font-size: 0.5rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(255, 160, 175, 0.95);
}

.orb-hud__sheet-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.35rem;
}

.orb-hud__sheet-actions button {
  border: 1px solid rgba(160, 210, 230, 0.35);
  border-radius: 999px;
  background: rgba(4, 16, 24, 0.45);
  color: rgba(220, 245, 255, 0.95);
  font: 0.58rem/1 system-ui, sans-serif;
  padding: 0.28rem 0.55rem;
  cursor: pointer;
}

.orb-hud__sheet-go {
  border-color: rgba(90, 255, 190, 0.55) !important;
  color: rgba(210, 255, 230, 0.98) !important;
  background: rgba(10, 40, 28, 0.55) !important;
}

@media (prefers-reduced-motion: reduce) {
  .orb-hud__arc,
  .orb-hud__arc::after,
  .orb-hud__chip--prime[data-on='true'],
  .orb-hud__telemetry-pulse[data-tone='running'],
  .orb-hud__sheet {
    animation: none;
  }
}
</style>

<style scoped src="./mission-control-autonomy-control.css"></style>
