import { nextTick, ref, type Ref } from 'vue';

import {
  persistAgentComposerHistory,
  readStoredAgentComposerHistory,
  recordAgentComposerHistoryEntry,
  stepAgentComposerHistory,
} from '../../lib/agent-dock-composer-history';

type UseComposerHistoryOptions = {
  inputRef: Ref<HTMLTextAreaElement | null>;
  syncComposerHeight: () => void;
  clearComposerImages: () => void;
  composerImages: Ref<unknown[]>;
  getDraft: () => string;
  setDraft: (value: string) => void;
};

export function useComposerHistory(options: UseComposerHistoryOptions) {
  const {
    inputRef,
    syncComposerHeight,
    clearComposerImages,
    composerImages,
    getDraft,
    setDraft,
  } = options;

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
    setDraft(draft);
    void nextTick(() => {
      applyingHistoryDraft.value = false;
      syncComposerHeight();
      if (!inputRef.value) {
        return;
      }
      const caret = inputRef.value.value.length;
      inputRef.value.setSelectionRange(caret, caret);
    });
  }

  function handleHistory(direction: 'previous' | 'next'): void {
    // Refresh from storage so prompts sent from the VAXON operator bar are included.
    if (composerHistoryWorkspaceId.value) {
      composerHistory.value = readStoredAgentComposerHistory(composerHistoryWorkspaceId.value);
    }
    const step = stepAgentComposerHistory({
      entries: composerHistory.value,
      index: composerHistoryIndex.value,
      scratch: composerHistoryScratch.value,
      currentDraft: getDraft(),
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
    const trimmed = draft.trim();
    if (!trimmed) {
      return;
    }
    // Record whenever a prompt was consumed (sent or queued).
    composerHistory.value = recordAgentComposerHistoryEntry(composerHistory.value, trimmed);
    persistCurrentComposerHistory();
    resetComposerHistoryNavigation();
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
