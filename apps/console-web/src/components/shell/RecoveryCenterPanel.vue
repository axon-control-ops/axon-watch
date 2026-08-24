<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';

import {
  acknowledgeRecovery,
  clearWorkspaceStaleRecovery,
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
const clearing = ref(false);
const clearResult = ref<string | null>(null);

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

async function clearWorkspaceStaleState(): Promise<void> {
  const workspaceId = String(shell.currentWorkspace?.workspace_id || '').trim();
  if (!workspaceId || clearing.value) return;
  clearing.value = true;
  clearResult.value = null;
  try {
    const preview = await clearWorkspaceStaleRecovery(workspaceId, false);
    if (!preview.candidate_count) {
      clearResult.value = 'No failed or stale workspace state remains.';
      await refresh();
      return;
    }
    const confirmed = window.confirm(
      `Clear ${preview.candidate_count} failed/stale recovery item(s) for this workspace? ` +
        `This cancels ${preview.task_ids.length} linked active task(s), stops matching live runs, ` +
        'and keeps run history, evidence, checkpoints, and worktrees.',
    );
    if (!confirmed) return;
    const result = await clearWorkspaceStaleRecovery(workspaceId, true);
    clearResult.value = result.errors.length
      ? `Reset completed with ${result.errors.length} item(s) needing inspection.`
      : `Workspace reset: ${result.acknowledged_recoveries.length} recovery item(s) cleared and ` +
        `${result.cancelled_tasks.length} task(s) cancelled.`;
    await refresh();
  } catch (clearError) {
    clearResult.value = clearError instanceof Error ? clearError.message : 'Workspace reset failed.';
  } finally {
    clearing.value = false;
  }
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
        <div class="recovery-center__header-actions">
          <button
            type="button"
            class="recovery-center__clear"
            :disabled="clearing"
            @click="clearWorkspaceStaleState"
          >
            {{ clearing ? 'Clearing…' : 'Clear stale state' }}
          </button>
          <button type="button" class="recovery-center__dismiss" @click="dismiss">Done</button>
        </div>
      </header>
      <p v-if="clearResult" class="recovery-center__result" role="status">{{ clearResult }}</p>
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
