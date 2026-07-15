import type { Ref } from 'vue';

import { fetchRunHistory, fetchRuns, fetchWorkspaces, registerWorkspaceBinding } from '../../../api/control-plane';
import type { RunRecord, WorkspaceRecord } from '../../../contracts/canonical';
import { mergeOperatorWorkspaceCatalog } from '../../../lib/operator-workspace-catalog';
import { persistOperatorWorkspaceId } from '../../../lib/operator-workspace-selection';
import { resolveOperatorWorkspaceId } from '../../../lib/mockup-shell-view';
import type { RunHistorySnapshot } from '../../../lib/run-history-view';
import { selectPrimaryRun } from '../../shell-run-selection';
import type { RunsLoadState, WorkspacesLoadState } from '../types';

interface CreateCatalogLoadersSliceInput {
  workspaces: Ref<WorkspaceRecord[]>;
  currentWorkspace: Ref<WorkspaceRecord | null>;
  operatorPinnedWorkspaceId: Ref<string | null>;
  workspacesLoadState: Ref<WorkspacesLoadState>;
  workspacesError: Ref<string | null>;
  runs: Ref<RunRecord[]>;
  activeRun: Ref<RunRecord | null>;
  runsLoadState: Ref<RunsLoadState>;
  runsError: Ref<string | null>;
  runHistorySnapshot: Ref<RunHistorySnapshot | null>;
  runHistoryLoadState: Ref<'idle' | 'loading' | 'loaded' | 'error'>;
}

export function createCatalogLoadersSlice(input: CreateCatalogLoadersSliceInput) {
  function syncCurrentWorkspace(preferredWorkspaceId?: string | null): void {
    if (input.workspaces.value.length === 0) {
      input.currentWorkspace.value = null;
      return;
    }

    const targetWorkspaceId = resolveOperatorWorkspaceId({
      explicitPreferredId:
        preferredWorkspaceId !== undefined && preferredWorkspaceId !== null
          ? preferredWorkspaceId
          : null,
      pinnedWorkspaceId: input.operatorPinnedWorkspaceId.value,
      workspaces: input.workspaces.value,
      activeRun: input.activeRun.value,
    });

    input.currentWorkspace.value =
      input.workspaces.value.find((workspace) => workspace.workspace_id === targetWorkspaceId) ??
      input.workspaces.value[0] ??
      null;
  }

  function shouldAutoSyncWorkspaceFromRuns(): boolean {
    return !input.operatorPinnedWorkspaceId.value;
  }

  async function loadWorkspaces(options: { sync?: boolean } = {}): Promise<void> {
    input.workspacesLoadState.value = 'loading';
    input.workspacesError.value = null;

    try {
      const snapshot = await fetchWorkspaces({ scope: 'operator' });
      input.workspaces.value = mergeOperatorWorkspaceCatalog(snapshot.items);
      const visibleIds = new Set(input.workspaces.value.map((workspace) => workspace.workspace_id));
      if (
        input.operatorPinnedWorkspaceId.value &&
        !visibleIds.has(input.operatorPinnedWorkspaceId.value)
      ) {
        input.operatorPinnedWorkspaceId.value = null;
        persistOperatorWorkspaceId(null);
      }
      if (options.sync !== false && shouldAutoSyncWorkspaceFromRuns()) {
        syncCurrentWorkspace();
      }
      input.workspacesLoadState.value = 'loaded';
    } catch (error) {
      input.workspacesLoadState.value = 'error';
      input.workspacesError.value =
        error instanceof Error ? error.message : 'workspaces request failed';
    }
  }

  async function loadRuns(options: { sync?: boolean; background?: boolean } = {}): Promise<void> {
    const background =
      options.background === true || input.runsLoadState.value === 'loaded';
    if (!background) {
      input.runsLoadState.value = 'loading';
      input.runsError.value = null;
    }

    try {
      const snapshot = await fetchRuns();
      input.runs.value = snapshot.items;
      input.activeRun.value = selectPrimaryRun(snapshot.items);
      if (options.sync !== false && shouldAutoSyncWorkspaceFromRuns()) {
        syncCurrentWorkspace(input.activeRun.value?.workspace_id ?? null);
      }
      input.runsLoadState.value = 'loaded';
    } catch (error) {
      if (!background) {
        input.runsLoadState.value = 'error';
        input.runsError.value = error instanceof Error ? error.message : 'runs request failed';
      }
    }
  }

  async function loadRunHistory(runId: string | null): Promise<void> {
    if (!runId) {
      input.runHistorySnapshot.value = null;
      input.runHistoryLoadState.value = 'idle';
      return;
    }

    input.runHistoryLoadState.value = 'loading';
    try {
      input.runHistorySnapshot.value = await fetchRunHistory(runId);
      input.runHistoryLoadState.value = 'loaded';
    } catch {
      input.runHistorySnapshot.value = null;
      input.runHistoryLoadState.value = 'error';
    }
  }

  async function registerWorkspace(options: {
    workspaceId: string;
    projectRoot: string;
    displayName?: string;
  }): Promise<WorkspaceRecord> {
    const response = await registerWorkspaceBinding({
      workspace_id: options.workspaceId,
      project_root: options.projectRoot,
      display_name: options.displayName ?? null,
    });
    await loadWorkspaces({ sync: false });
    return response.workspace;
  }

  return {
    syncCurrentWorkspace,
    shouldAutoSyncWorkspaceFromRuns,
    loadWorkspaces,
    loadRuns,
    loadRunHistory,
    registerWorkspace,
  };
}
