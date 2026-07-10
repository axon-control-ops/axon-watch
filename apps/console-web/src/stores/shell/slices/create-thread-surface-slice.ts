import type { Ref } from 'vue';

import {
  clearActiveIdeThreadIdForWorkspace,
  writeActiveIdeThreadIdForWorkspace,
} from '../../../lib/ide-thread-tabs-prefs';
import {
  isActiveWorkspaceSurface,
  threadSurfaceForLayout,
  type ThreadSurface,
} from '../../../lib/thread-surface-view';
import type { WorkspaceRecord } from '../../../contracts/canonical';
import type { LayoutMode } from '../types';

interface CreateThreadSurfaceSliceInput {
  layoutMode: Ref<LayoutMode>;
  currentWorkspace: Ref<WorkspaceRecord | null>;
  workspaceSurfaceThreadIds: Ref<Record<string, Partial<Record<ThreadSurface, string>>>>;
}

export function createThreadSurfaceSlice(input: CreateThreadSurfaceSliceInput) {
  function currentThreadSurface(): ThreadSurface {
    return threadSurfaceForLayout(input.layoutMode.value);
  }

  function isViewingWorkspaceSurface(workspaceId: string, surface: ThreadSurface): boolean {
    return isActiveWorkspaceSurface({
      currentWorkspaceId: input.currentWorkspace.value?.workspace_id ?? null,
      targetWorkspaceId: workspaceId,
      currentSurface: currentThreadSurface(),
      targetSurface: surface,
    });
  }

  function getWorkspaceSurfaceThreadId(
    workspaceId: string,
    surface: ThreadSurface,
  ): string | null {
    return input.workspaceSurfaceThreadIds.value[workspaceId]?.[surface] ?? null;
  }

  function setWorkspaceSurfaceThreadId(
    workspaceId: string,
    surface: ThreadSurface,
    threadId: string,
  ): void {
    input.workspaceSurfaceThreadIds.value = {
      ...input.workspaceSurfaceThreadIds.value,
      [workspaceId]: {
        ...(input.workspaceSurfaceThreadIds.value[workspaceId] ?? {}),
        [surface]: threadId,
      },
    };
    if (surface === 'ide') {
      writeActiveIdeThreadIdForWorkspace(workspaceId, threadId);
    }
  }

  function clearWorkspaceSurfaceThreadId(workspaceId: string, surface: ThreadSurface): void {
    const next = { ...input.workspaceSurfaceThreadIds.value };
    const record = { ...(next[workspaceId] ?? {}) };
    delete record[surface];
    if (Object.keys(record).length) {
      next[workspaceId] = record;
    } else {
      delete next[workspaceId];
    }
    input.workspaceSurfaceThreadIds.value = next;
    if (surface === 'ide') {
      clearActiveIdeThreadIdForWorkspace(workspaceId);
    }
  }

  return {
    currentThreadSurface,
    isViewingWorkspaceSurface,
    getWorkspaceSurfaceThreadId,
    setWorkspaceSurfaceThreadId,
    clearWorkspaceSurfaceThreadId,
  };
}
