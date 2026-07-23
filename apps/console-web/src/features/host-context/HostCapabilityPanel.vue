<script setup lang="ts">
import { onMounted, ref } from 'vue';

import type { HostArtifactRecord, OperatorReminderRecord } from '../../contracts/canonical';
import { isDesktopRuntime, detectDesktopCapabilities } from '../../lib/desktop-capability';
import HostArtifactCard from './HostArtifactCard.vue';
import {
  fetchDueReminders,
  fetchHostArtifacts,
  pauseHostAwareness,
  patchReminder,
  requestHostAction,
} from './host-context-api';

const artifacts = ref<HostArtifactRecord[]>([]);
const reminders = ref<OperatorReminderRecord[]>([]);
const status = ref('');
const caps = detectDesktopCapabilities();
const desktop = isDesktopRuntime(caps);

onMounted(async () => {
  try {
    artifacts.value = await fetchHostArtifacts();
    reminders.value = await fetchDueReminders();
  } catch (error) {
    status.value = error instanceof Error ? error.message : 'Host context unavailable';
  }
});

async function onOpen(artifact: HostArtifactRecord): Promise<void> {
  if (!desktop) {
    status.value = 'Open/reveal requires the desktop shell';
    return;
  }
  const result = await requestHostAction({
    deviceId: artifact.device_id,
    action: 'open.path',
    path: artifact.path,
  });
  status.value = result.accepted ? 'Open queued' : String(result.decision.reason ?? 'blocked');
}

async function onReveal(artifact: HostArtifactRecord): Promise<void> {
  if (!desktop) {
    status.value = 'Open/reveal requires the desktop shell';
    return;
  }
  const result = await requestHostAction({
    deviceId: artifact.device_id,
    action: 'reveal.path',
    path: artifact.path,
  });
  status.value = result.accepted ? 'Reveal queued' : String(result.decision.reason ?? 'blocked');
}

async function snooze(reminder: OperatorReminderRecord): Promise<void> {
  await patchReminder(reminder.memory_id, { status: 'snoozed' });
  reminders.value = await fetchDueReminders();
}

async function dismiss(reminder: OperatorReminderRecord): Promise<void> {
  await patchReminder(reminder.memory_id, { status: 'dismissed', dismiss_reason: 'operator' });
  reminders.value = await fetchDueReminders();
}

async function pause(): Promise<void> {
  await pauseHostAwareness(true);
  status.value = 'Host awareness paused';
}
</script>

<template>
  <section class="host-capability-panel glass-surface glass-surface--tier-1">
    <header class="host-capability-panel__head">
      <h2>Host context</h2>
      <span class="host-capability-panel__runtime">{{ caps.runtime }}</span>
    </header>
    <p v-if="status" class="host-capability-panel__status">{{ status }}</p>
    <div class="host-capability-panel__actions">
      <button type="button" @click="pause">Pause awareness</button>
    </div>
    <div v-if="reminders.length" class="host-capability-panel__block">
      <h3>Due reminders</h3>
      <ul>
        <li v-for="item in reminders" :key="item.memory_id">
          <strong>{{ item.title }}</strong>
          <span>{{ item.why_now || item.due_at }}</span>
          <button type="button" @click="snooze(item)">Snooze</button>
          <button type="button" @click="dismiss(item)">Dismiss</button>
        </li>
      </ul>
    </div>
    <div class="host-capability-panel__block">
      <h3>Recent artifacts</h3>
      <div class="host-capability-panel__grid">
        <HostArtifactCard
          v-for="artifact in artifacts"
          :key="artifact.artifact_id"
          :artifact="artifact"
          :desktop-actions="desktop && caps.openReveal"
          @open="onOpen"
          @reveal="onReveal"
        />
        <p v-if="!artifacts.length" class="host-capability-panel__empty">No indexed artifacts yet.</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.host-capability-panel {
  display: grid;
  gap: 0.75rem;
  padding: 0.85rem;
}
.host-capability-panel__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.host-capability-panel__head h2,
.host-capability-panel__block h3 {
  margin: 0;
  font-size: var(--font-size-ui);
}
.host-capability-panel__runtime {
  color: var(--text-hud);
  font-size: var(--font-size-caption);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.host-capability-panel__status,
.host-capability-panel__empty {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--font-size-meta);
}
.host-capability-panel__grid {
  display: grid;
  gap: 0.5rem;
}
.host-capability-panel__block ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.45rem;
}
.host-capability-panel__block li {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 0.35rem 0.5rem;
  align-items: center;
  font-size: var(--font-size-meta);
}
.host-capability-panel button {
  appearance: none;
  border: 1px solid var(--border-glass);
  background: transparent;
  color: var(--text-hud);
  font: inherit;
  font-size: var(--font-size-caption);
  padding: 0.2rem 0.45rem;
  cursor: pointer;
}
</style>
