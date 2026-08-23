import { computed, ref } from 'vue';

import {
  fetchRecoveryCenter,
  type RecoveryCenterItem,
  type RecoveryCenterSnapshot,
} from '../../api/recovery-api';
import { attentionLabel } from '../../lib/recovery-center-view';

const open = ref(false);
const loading = ref(false);
const error = ref<string | null>(null);
const snapshot = ref<RecoveryCenterSnapshot | null>(null);

export const recoveryCenterOpen = computed(() => open.value);
export const recoveryCenterLoading = computed(() => loading.value);
export const recoveryCenterError = computed(() => error.value);
export const recoveryCenterSnapshot = computed(() => snapshot.value);
export const recoveryAttentionCount = computed(() => snapshot.value?.attention_count ?? 0);
export const recoveryAttentionLabel = computed(() => attentionLabel(recoveryAttentionCount.value));
export const recoveryCenterItems = computed<RecoveryCenterItem[]>(() => snapshot.value?.items ?? []);

export async function loadRecoveryCenter(workspaceId?: string | null): Promise<void> {
  loading.value = true;
  error.value = null;
  try {
    snapshot.value = await fetchRecoveryCenter(workspaceId);
  } catch (loadError) {
    error.value = loadError instanceof Error ? loadError.message : 'Recovery center failed to load.';
  } finally {
    loading.value = false;
  }
}

export async function openRecoveryCenter(workspaceId?: string | null): Promise<void> {
  open.value = true;
  await loadRecoveryCenter(workspaceId);
}

export function closeRecoveryCenter(): void {
  open.value = false;
}

export function resetRecoveryCenterForTests(): void {
  open.value = false;
  loading.value = false;
  error.value = null;
  snapshot.value = null;
}
