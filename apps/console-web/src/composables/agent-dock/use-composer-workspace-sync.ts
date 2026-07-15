import { nextTick, onMounted, onUnmounted, watch, type Ref } from 'vue';

import {
  persistWorkspaceComposerMode,
  readWorkspaceComposerMode,
} from '../../lib/composer-mode-prefs';
import { useShellStore } from '../../stores/shell';
import type { ComposerMode } from './use-composer-menus';
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
  closeMenus: () => void;
  syncComposerHeight: () => void;
  syncContextFromDraft: () => void;
  loadComposerHistoryForWorkspace: (workspaceId: string | null) => void;
  loadComposerImagesForWorkspace: (workspaceId: string | null) => void;
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
    () => shell.currentWorkspace?.workspace_id ?? null,
    (workspaceId) => {
      const restoredMode = readWorkspaceComposerMode(workspaceId) ?? defaultComposerMode;
      if (composerMode.value !== restoredMode) {
        restoringWorkspaceComposerMode = true;
        composerMode.value = restoredMode;
      }
      loadComposerHistoryForWorkspace(workspaceId);
      loadComposerImagesForWorkspace(workspaceId);
    },
    { immediate: true },
  );

  watch(composerMode, (mode) => {
    if (restoringWorkspaceComposerMode) {
      restoringWorkspaceComposerMode = false;
    } else {
      persistWorkspaceComposerMode(shell.currentWorkspace?.workspace_id, mode);
    }
    shell.setIdeDebugModeSelected(mode === 'debug');
  }, { immediate: true });

  watch(
    () => shell.ideAgentLinkedRun?.mode,
    (linkedMode) => {
      const storedMode = readWorkspaceComposerMode(shell.currentWorkspace?.workspace_id);
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
