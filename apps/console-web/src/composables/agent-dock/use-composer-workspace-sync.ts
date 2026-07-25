import { nextTick, onMounted, onUnmounted, watch, type Ref } from 'vue';

import {
  persistWorkspaceComposerMode,
  readWorkspaceComposerMode,
} from '../../lib/composer-mode-prefs';
import { useShellStore } from '../../stores/shell';
import type { ComposerMode } from './use-composer-menus';
import type { PlanSoftSwitchNotice, TeammateRouteNotice } from './use-composer-actions';
import { useComposerRestoreModeFocus } from './use-composer-restore-mode-focus';

type ShellStore = ReturnType<typeof useShellStore>;

type UseComposerWorkspaceSyncOptions = {
  shell: ShellStore;
  composerMode: Ref<ComposerMode>;
  defaultComposerMode: ComposerMode;
  inputRef: Ref<HTMLTextAreaElement | null>;
  applyingHistoryDraft: Ref<boolean>;
  composerHistoryIndex: Ref<number>;
  composerHistoryScratch: Ref<string>;
  planSoftSwitchNotice: Ref<PlanSoftSwitchNotice | null>;
  teammateRouteNotice: Ref<TeammateRouteNotice | null>;
  closeMenus: () => void;
  syncComposerHeight: () => void;
  syncContextFromDraft: () => void;
  loadComposerHistoryForWorkspace: (workspaceId: string | null) => void;
  loadComposerImagesForWorkspace: (
    workspaceId: string | null,
    threadId?: string | null,
  ) => void;
  disposeComposerImagesPersistTimer: () => void;
  persistCurrentComposerImages: () => Promise<void>;
  revokeAllComposerImagePreviews: () => void;
};

export function useComposerWorkspaceSync(options: UseComposerWorkspaceSyncOptions): void {
  const {
    shell,
    composerMode,
    defaultComposerMode,
    inputRef,
    applyingHistoryDraft,
    composerHistoryIndex,
    composerHistoryScratch,
    planSoftSwitchNotice,
    teammateRouteNotice,
    closeMenus,
    syncComposerHeight,
    syncContextFromDraft,
    loadComposerHistoryForWorkspace,
    loadComposerImagesForWorkspace,
    disposeComposerImagesPersistTimer,
    persistCurrentComposerImages,
    revokeAllComposerImagePreviews,
  } = options;

  let restoringWorkspaceComposerMode = false;
  let lastSyncedWorkspaceId: string | null = null;
  let lastSyncedThreadId: string | null = null;
  let hasSyncedContext = false;

  function handleDocumentClick(): void {
    closeMenus();
  }

  watch(
    () => shell.ideComposerDraft,
    () => {
      const fromHistory = applyingHistoryDraft.value;
      if (fromHistory) {
        applyingHistoryDraft.value = false;
      } else if (composerHistoryIndex.value >= 0) {
        composerHistoryIndex.value = -1;
        composerHistoryScratch.value = '';
      }
      void nextTick(syncComposerHeight);
      syncContextFromDraft();
    },
  );

  watch(
    () => ({
      workspaceId: shell.currentWorkspace?.workspace_id ?? null,
      threadId: shell.activeIdeThreadId ?? null,
    }),
    ({ workspaceId, threadId }) => {
      const workspaceChanged = workspaceId !== lastSyncedWorkspaceId;
      const threadChanged = threadId !== lastSyncedThreadId;
      if (!workspaceChanged && !threadChanged) {
        return;
      }

      // Persist outgoing thread mode before restoring the incoming tab.
      if (lastSyncedWorkspaceId && lastSyncedThreadId && !restoringWorkspaceComposerMode) {
        persistWorkspaceComposerMode(
          lastSyncedWorkspaceId,
          composerMode.value,
          sessionStorage,
          lastSyncedThreadId,
        );
        void persistCurrentComposerImages();
      }

      lastSyncedWorkspaceId = workspaceId;
      lastSyncedThreadId = threadId;

      const restoredMode =
        readWorkspaceComposerMode(workspaceId, sessionStorage, threadId) ?? defaultComposerMode;
      if (composerMode.value !== restoredMode) {
        restoringWorkspaceComposerMode = true;
        composerMode.value = restoredMode;
      }
      planSoftSwitchNotice.value = null;
      if (hasSyncedContext && workspaceChanged) {
        teammateRouteNotice.value = null;
      }
      hasSyncedContext = true;
      if (workspaceChanged) {
        loadComposerHistoryForWorkspace(workspaceId);
      }
      loadComposerImagesForWorkspace(workspaceId, threadId);
      void nextTick(syncComposerHeight);
      syncContextFromDraft();
    },
    { immediate: true },
  );

  watch(composerMode, (mode) => {
    if (restoringWorkspaceComposerMode) {
      restoringWorkspaceComposerMode = false;
    } else {
      persistWorkspaceComposerMode(
        shell.currentWorkspace?.workspace_id,
        mode,
        sessionStorage,
        shell.activeIdeThreadId,
      );
    }
    shell.setIdeDebugModeSelected(mode === 'debug');
  }, { immediate: true });

  watch(
    () => shell.ideAgentLinkedRun?.mode,
    (linkedMode) => {
      const storedMode = readWorkspaceComposerMode(
        shell.currentWorkspace?.workspace_id,
        sessionStorage,
        shell.activeIdeThreadId,
      );
      if (!storedMode && (linkedMode === 'agent' || linkedMode === 'debug')) {
        composerMode.value = linkedMode;
      }
    },
  );

  useComposerRestoreModeFocus({
    commandFocusToken: () => shell.commandFocusToken,
    composerMode,
    inputRef,
    syncComposerHeight,
  });

  onMounted(() => {
    syncComposerHeight();
    syncContextFromDraft();
    document.addEventListener('click', handleDocumentClick);
  });

  onUnmounted(() => {
    document.removeEventListener('click', handleDocumentClick);
    disposeComposerImagesPersistTimer();
    void persistCurrentComposerImages();
    revokeAllComposerImagePreviews();
  });
}
