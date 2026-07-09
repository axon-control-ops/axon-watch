import { nextTick, ref, type Ref } from 'vue';

import {
  persistAgentComposerHistory,
  readStoredAgentComposerHistory,
  recordAgentComposerHistoryEntry,
  stepAgentComposerHistory,
} from '../../lib/agent-dock-composer-history';
import { useShellStore } from '../../stores/shell';

type ShellStore = ReturnType<typeof useShellStore>;

type UseComposerHistoryOptions = {
  shell: ShellStore;
  inputRef: Ref<HTMLTextAreaElement | null>;
  syncComposerHeight: () => void;
  clearComposerImages: () => void;
  composerImages: Ref<unknown[]>;
};

export function useComposerHistory(options: UseComposerHistoryOptions) {
  const { shell, inputRef, syncComposerHeight, clearComposerImages, composerImages } = options;

  const composerHistory = ref<string[]>([]);
  const composerHistoryWorkspaceId = ref<string | null>(null);
  const composerHistoryIndex = ref(-1);
  const composerHistoryScratch = ref('');
  const applyingHistoryDraft = ref(false);

  function resetComposerHistoryNavigation(): void {
    composerHistoryIndex.value = -1;
    composerHistoryScratch.value = '';
  }

  function loadComposerHistoryForWorkspace(workspaceId: string | null | undefined): void {
    const nextWorkspaceId = workspaceId?.trim() || null;
    if (composerHistoryWorkspaceId.value === nextWorkspaceId) {
      return;
    }
    composerHistoryWorkspaceId.value = nextWorkspaceId;
    composerHistory.value = readStoredAgentComposerHistory(nextWorkspaceId);
    resetComposerHistoryNavigation();
  }

  function persistCurrentComposerHistory(): void {
    persistAgentComposerHistory(composerHistoryWorkspaceId.value, composerHistory.value);
  }

  function applyHistoryDraft(draft: string): void {
    applyingHistoryDraft.value = true;
    shell.restoreComposerDraft(draft);
    void nextTick(() => {
      syncComposerHeight();
      if (!inputRef.value) {
        return;
      }
      const caret = inputRef.value.value.length;
      inputRef.value.setSelectionRange(caret, caret);
    });
  }

  function handleHistory(direction: 'previous' | 'next'): void {
    const step = stepAgentComposerHistory({
      entries: composerHistory.value,
      index: composerHistoryIndex.value,
      scratch: composerHistoryScratch.value,
      currentDraft: shell.ideComposerDraft,
      direction,
    });
    composerHistoryIndex.value = step.index;
    composerHistoryScratch.value = step.scratch;
    applyHistoryDraft(step.draft);
  }

  function recordComposerHistoryIfSent(draft: string): void {
    if (composerImages.value.length) {
      clearComposerImages();
    }
    if (draft && !shell.ideComposerDraft.trim() && shell.commandMutationState === 'idle') {
      composerHistory.value = recordAgentComposerHistoryEntry(composerHistory.value, draft);
      persistCurrentComposerHistory();
      resetComposerHistoryNavigation();
    }
  }

  return {
    composerHistory,
    composerHistoryWorkspaceId,
    composerHistoryIndex,
    composerHistoryScratch,
    applyingHistoryDraft,
    resetComposerHistoryNavigation,
    loadComposerHistoryForWorkspace,
    persistCurrentComposerHistory,
    applyHistoryDraft,
    handleHistory,
    recordComposerHistoryIfSent,
  };
}
