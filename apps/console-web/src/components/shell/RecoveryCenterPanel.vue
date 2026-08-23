<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue';

import {
  acknowledgeRecovery,
  reconcilePlatform,
  resumeRecoveredRun,
  type RecoveryCenterItem,
} from '../../api/recovery-api';
import { groupRecoveryItems, toRecoveryItemView } from '../../lib/recovery-center-view';
import { useShellStore } from '../../stores/shell';
import {
  closeRecoveryCenter,
  loadRecoveryCenter,
  recoveryCenterError,
  recoveryCenterItems,
  recoveryCenterLoading,
  recoveryCenterOpen,
  recoveryAttentionCount,
} from '../../features/recovery-center/recovery-overlay-state';

const shell = useShellStore();
const open = recoveryCenterOpen;
const loading = recoveryCenterLoading;
const error = recoveryCenterError;
const items = recoveryCenterItems;
const attention = recoveryAttentionCount;

const grouped = computed(() => groupRecoveryItems(items.value));
const buckets = computed(() =>
  Object.entries(grouped.value).filter(([, list]) => list.length > 0),
);

function dismiss(): void {
  closeRecoveryCenter();
}

function onKeydown(event: KeyboardEvent): void {
  if (open.value && event.key === 'Escape') {
    event.preventDefault();
    dismiss();
  }
}

async function refresh(): Promise<void> {
  await loadRecoveryCenter(shell.currentWorkspace?.workspace_id);
}

async function onAction(item: RecoveryCenterItem, action: string): Promise<void> {
  if (action === 'Resume') {
    await resumeRecoveredRun(item.run_id);
  } else if (action === 'Acknowledge') {
    const recoveryId = String(item.recovery_id || '');
    if (recoveryId) {
      await acknowledgeRecovery(recoveryId);
    }
  } else if (action === 'Reconcile') {
    await reconcilePlatform(false);
  }
  await refresh();
}

onMounted(() => window.addEventListener('keydown', onKeydown));
onUnmounted(() => window.removeEventListener('keydown', onKeydown));
</script>

<template>
  <div
    v-if="open"
    class="recovery-center"
    role="dialog"
    aria-modal="true"
    aria-label="Recovery Center"
  >
    <div class="recovery-center__veil" aria-hidden="true" @click="dismiss" />
    <article class="recovery-center__panel">
      <header class="recovery-center__header">
        <div>
          <p class="recovery-center__eyebrow">Recovery Center</p>
          <h2 class="recovery-center__title">
            ATTENTION {{ attention }}
          </h2>
          <p class="recovery-center__goal">
            Reconcile, resume, retry, or cancel. Clearing never deletes historical evidence.
          </p>
        </div>
        <button type="button" class="recovery-center__dismiss" @click="dismiss">Done</button>
      </header>
      <p v-if="loading">Loading authoritative recovery state…</p>
      <p v-else-if="error">{{ error }}</p>
      <div v-else class="recovery-center__body">
        <section v-for="[bucket, list] in buckets" :key="bucket" class="recovery-center__bucket">
          <h3>{{ bucket }} ({{ list.length }})</h3>
          <article v-for="item in list" :key="item.run_id" class="recovery-center__item">
            <p class="recovery-center__item-title">{{ toRecoveryItemView(item).title }}</p>
            <p><strong>What happened.</strong> {{ toRecoveryItemView(item).whatHappened }}</p>
            <p><strong>Why stale.</strong> {{ toRecoveryItemView(item).whyStale }}</p>
            <p><strong>Next step.</strong> {{ toRecoveryItemView(item).nextStep }}</p>
            <p><strong>Last progress.</strong> {{ toRecoveryItemView(item).lastProgress }}</p>
            <div class="recovery-center__actions">
              <button
                v-for="action in item.actions"
                :key="action"
                type="button"
                @click="onAction(item, action)"
              >
                {{ action }}
              </button>
            </div>
          </article>
        </section>
        <p v-if="!items.length">No stale, failed, or blocked runs in this workspace.</p>
      </div>
    </article>
  </div>
</template>

<style scoped src="./recovery-center.css"></style>
