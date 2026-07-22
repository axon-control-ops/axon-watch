import { computed, onScopeDispose, ref, watch, type Ref } from 'vue';

import {
  cancelWorkspaceTask,
  createWorkspaceTask,
  fetchWorkspaceTasks,
  type CreateWorkspaceTaskInput,
  type WorkspaceTaskRecord,
} from '../../../api/tasks-api';
import type { WorkspaceRecord } from '../../../contracts/canonical';
import { COMPANY_REFRESH_MS } from '../../../lib/ui-refresh-guardrails';

interface CreateWorkspaceTasksSliceInput {
  currentWorkspace: Ref<WorkspaceRecord | null>;
}

export function createWorkspaceTasksSlice(input: CreateWorkspaceTasksSliceInput) {
  const workspaceTasksById = ref<Record<string, WorkspaceTaskRecord[]>>({});
  const workspaceTasksError = ref<string | null>(null);
  const workspaceTasksMutating = ref(false);
  let refreshTimer: ReturnType<typeof setInterval> | null = null;

  function stopRefreshTimer(): void {
    if (refreshTimer !== null) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  }

  function startRefreshTimer(workspaceId: string): void {
    stopRefreshTimer();
    refreshTimer = setInterval(() => {
      void loadWorkspaceTasks(workspaceId);
    }, COMPANY_REFRESH_MS);
  }

  async function loadWorkspaceTasks(workspaceId: string): Promise<void> {
    const cleaned = workspaceId.trim();
    if (!cleaned) {
      return;
    }
    try {
      const snapshot = await fetchWorkspaceTasks(cleaned, { limit: 100 });
      workspaceTasksById.value = {
        ...workspaceTasksById.value,
        [cleaned]: snapshot.items ?? [],
      };
      workspaceTasksError.value = null;
    } catch (error) {
      workspaceTasksError.value =
        error instanceof Error ? error.message : 'Failed to load workspace tasks';
    }
  }

  async function createCurrentWorkspaceTask(
    inputBody: CreateWorkspaceTaskInput,
  ): Promise<WorkspaceTaskRecord | null> {
    const workspaceId = input.currentWorkspace.value?.workspace_id?.trim() ?? '';
    if (!workspaceId) {
      workspaceTasksError.value = 'Select a workspace before creating a task';
      return null;
    }
    workspaceTasksMutating.value = true;
    try {
      const created = await createWorkspaceTask(workspaceId, inputBody);
      const previous = workspaceTasksById.value[workspaceId] ?? [];
      workspaceTasksById.value = {
        ...workspaceTasksById.value,
        [workspaceId]: [created, ...previous.filter((row) => row.task_id !== created.task_id)],
      };
      workspaceTasksError.value = null;
      return created;
    } catch (error) {
      workspaceTasksError.value =
        error instanceof Error ? error.message : 'Failed to create workspace task';
      return null;
    } finally {
      workspaceTasksMutating.value = false;
    }
  }

  async function cancelCurrentWorkspaceTask(taskId: string): Promise<boolean> {
    const workspaceId = input.currentWorkspace.value?.workspace_id?.trim() ?? '';
    const cleanedTask = taskId.trim();
    if (!workspaceId || !cleanedTask) {
      return false;
    }
    workspaceTasksMutating.value = true;
    try {
      const cancelled = await cancelWorkspaceTask(cleanedTask);
      const previous = workspaceTasksById.value[workspaceId] ?? [];
      workspaceTasksById.value = {
        ...workspaceTasksById.value,
        [workspaceId]: previous.map((row) =>
          row.task_id === cancelled.task_id ? cancelled : row,
        ),
      };
      workspaceTasksError.value = null;
      return true;
    } catch (error) {
      workspaceTasksError.value =
        error instanceof Error ? error.message : 'Failed to cancel workspace task';
      return false;
    } finally {
      workspaceTasksMutating.value = false;
    }
  }

  const workspaceTasksForCurrentWorkspace = computed(() => {
    const workspaceId = input.currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return [] as WorkspaceTaskRecord[];
    }
    return workspaceTasksById.value[workspaceId] ?? [];
  });

  watch(
    () => input.currentWorkspace.value?.workspace_id ?? null,
    (workspaceId) => {
      stopRefreshTimer();
      if (workspaceId) {
        void loadWorkspaceTasks(workspaceId);
        startRefreshTimer(workspaceId);
      }
    },
    { immediate: true },
  );

  onScopeDispose(() => {
    stopRefreshTimer();
  });

  return {
    workspaceTasksById,
    workspaceTasksForCurrentWorkspace,
    workspaceTasksError,
    workspaceTasksMutating,
    loadWorkspaceTasks,
    createCurrentWorkspaceTask,
    cancelCurrentWorkspaceTask,
  };
}
