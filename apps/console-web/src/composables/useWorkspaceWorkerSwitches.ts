/** Workspaces panel Off/On switches for continuous workers per workspace. */

import { onMounted, onUnmounted, ref, type Ref } from 'vue';

import {
  fetchWorkerSchedulerStatus,
  patchWorkspaceWorkerEnabled,
} from '../api/worker-scheduler-api';

const workspaceEnabled = ref<Record<string, boolean>>({});
const loading = ref(false);
const savingId = ref<string | null>(null);
const error = ref<string | null>(null);
let sharedLoads = 0;
let pollTimer: ReturnType<typeof setInterval> | null = null;

async function reloadWorkspaceSwitches(): Promise<void> {
  loading.value = true;
  try {
    const status = await fetchWorkerSchedulerStatus();
    workspaceEnabled.value = { ...(status.workspace_enabled ?? {}) };
    error.value = null;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Could not load workspace switches';
  } finally {
    loading.value = false;
  }
}

function isWorkspaceWorkerOn(workspaceId: string): boolean {
  const key = workspaceId.trim();
  if (!key) {
    return false;
  }
  if (key in workspaceEnabled.value) {
    return Boolean(workspaceEnabled.value[key]);
  }
  return true;
}

async function setWorkspaceWorkerOn(workspaceId: string, enabled: boolean): Promise<boolean> {
  const key = workspaceId.trim();
  if (!key || savingId.value) {
    return false;
  }
  savingId.value = key;
  const previous = { ...workspaceEnabled.value };
  workspaceEnabled.value = { ...workspaceEnabled.value, [key]: enabled };
  try {
    const response = await patchWorkspaceWorkerEnabled(key, enabled);
    workspaceEnabled.value = { ...(response.workspace_enabled ?? workspaceEnabled.value) };
    error.value = null;
    return true;
  } catch (err) {
    workspaceEnabled.value = previous;
    error.value = err instanceof Error ? err.message : 'Could not update workspace switch';
    return false;
  } finally {
    savingId.value = null;
  }
}

export function useWorkspaceWorkerSwitches(options?: {
  pollMs?: number;
  autoLoad?: boolean;
}): {
  workspaceEnabled: Ref<Record<string, boolean>>;
  loading: Ref<boolean>;
  savingId: Ref<string | null>;
  error: Ref<string | null>;
  isWorkspaceWorkerOn: (workspaceId: string) => boolean;
  setWorkspaceWorkerOn: (workspaceId: string, enabled: boolean) => Promise<boolean>;
  reloadWorkspaceSwitches: () => Promise<void>;
} {
  const pollMs = options?.pollMs ?? 12_000;
  const autoLoad = options?.autoLoad ?? true;

  onMounted(() => {
    sharedLoads += 1;
    if (autoLoad) {
      void reloadWorkspaceSwitches();
    }
    if (sharedLoads === 1 && pollMs > 0) {
      pollTimer = setInterval(() => {
        void reloadWorkspaceSwitches();
      }, pollMs);
    }
  });

  onUnmounted(() => {
    sharedLoads = Math.max(0, sharedLoads - 1);
    if (sharedLoads === 0 && pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  });

  return {
    workspaceEnabled,
    loading,
    savingId,
    error,
    isWorkspaceWorkerOn,
    setWorkspaceWorkerOn,
    reloadWorkspaceSwitches,
  };
}
