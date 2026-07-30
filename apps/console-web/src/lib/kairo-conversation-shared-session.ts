import { ref, watch } from 'vue';

import {
  persistAgentComposerHistory,
  readStoredAgentComposerHistory,
  recordAgentComposerHistoryEntry,
  shouldRecallNextAgentComposerHistory,
  shouldRecallPreviousAgentComposerHistory,
  stepAgentComposerHistory,
} from './agent-dock-composer-history';
import {
  persistKairoConversationDraft,
  readStoredKairoConversationDraft,
} from './kairo-conversation-draft-prefs';
import { useShellStore } from '../stores/shell';

/** Shared across operator bar + IDE Kairo mode so draft survives remounts. */
export const sharedKairoDraft = ref('');
export const sharedKairoPending = ref(false);
export const sharedKairoThinkingLine = ref('');

const sharedHistory = ref<string[]>([]);
const sharedHistoryWorkspaceId = ref<string | null>(null);
const sharedHistoryIndex = ref(-1);
const sharedHistoryScratch = ref('');
let applyingSharedHistoryDraft = false;
let draftPersistTimer: ReturnType<typeof setTimeout> | null = null;
let draftPersistenceWired = false;
let lastDraftWorkspaceId = '';

function schedulePersistSharedDraft(workspaceId: string): void {
  if (typeof window === 'undefined') {
    return;
  }
  if (draftPersistTimer) {
    clearTimeout(draftPersistTimer);
  }
  draftPersistTimer = setTimeout(() => {
    draftPersistTimer = null;
    persistKairoConversationDraft(workspaceId, sharedKairoDraft.value);
  }, 140);
}

function resetSharedHistoryNavigation(): void {
  sharedHistoryIndex.value = -1;
  sharedHistoryScratch.value = '';
}

function loadSharedHistoryForWorkspace(workspaceId: string): void {
  const nextWorkspaceId = workspaceId.trim() || null;
  if (sharedHistoryWorkspaceId.value === nextWorkspaceId) {
    return;
  }
  sharedHistoryWorkspaceId.value = nextWorkspaceId;
  sharedHistory.value = readStoredAgentComposerHistory(nextWorkspaceId);
  resetSharedHistoryNavigation();
}

export function recordSharedKairoHistoryEntry(draft: string): void {
  const trimmed = draft.trim();
  if (!trimmed) {
    return;
  }
  sharedHistory.value = recordAgentComposerHistoryEntry(sharedHistory.value, trimmed);
  persistAgentComposerHistory(sharedHistoryWorkspaceId.value, sharedHistory.value);
  resetSharedHistoryNavigation();
}

export function wireSharedKairoDraftPersistence(
  shell: ReturnType<typeof useShellStore>,
): void {
  if (draftPersistenceWired) {
    return;
  }
  draftPersistenceWired = true;

  const hydrateForWorkspace = (workspaceId: string): void => {
    lastDraftWorkspaceId = workspaceId;
    loadSharedHistoryForWorkspace(workspaceId);
    sharedKairoDraft.value = workspaceId
      ? readStoredKairoConversationDraft(workspaceId)
      : '';
  };

  hydrateForWorkspace(shell.currentWorkspace?.workspace_id ?? '');

  watch(
    () => shell.currentWorkspace?.workspace_id ?? '',
    (workspaceId, previousWorkspaceId) => {
      if (draftPersistTimer) {
        clearTimeout(draftPersistTimer);
        draftPersistTimer = null;
      }
      if (previousWorkspaceId) {
        persistKairoConversationDraft(previousWorkspaceId, sharedKairoDraft.value);
      }
      hydrateForWorkspace(workspaceId);
    },
  );

  watch(sharedKairoDraft, () => {
    if (applyingSharedHistoryDraft) {
      applyingSharedHistoryDraft = false;
    } else if (sharedHistoryIndex.value >= 0) {
      resetSharedHistoryNavigation();
    }
    const workspaceId = shell.currentWorkspace?.workspace_id ?? lastDraftWorkspaceId;
    if (!workspaceId) {
      return;
    }
    schedulePersistSharedDraft(workspaceId);
  });
}

function stepSharedHistory(direction: 'previous' | 'next'): void {
  if (sharedHistoryWorkspaceId.value) {
    sharedHistory.value = readStoredAgentComposerHistory(sharedHistoryWorkspaceId.value);
  }
  const step = stepAgentComposerHistory({
    entries: sharedHistory.value,
    index: sharedHistoryIndex.value,
    scratch: sharedHistoryScratch.value,
    currentDraft: sharedKairoDraft.value,
    direction,
  });
  sharedHistoryIndex.value = step.index;
  sharedHistoryScratch.value = step.scratch;
  applyingSharedHistoryDraft = true;
  sharedKairoDraft.value = step.draft;
}

export function handleKairoComposerHistoryKeydown(
  event: KeyboardEvent,
  input: Pick<HTMLInputElement | HTMLTextAreaElement, 'selectionStart' | 'selectionEnd' | 'value'>,
): boolean {
  const keyEvent = {
    key: event.key,
    shiftKey: event.shiftKey,
    altKey: event.altKey,
    ctrlKey: event.ctrlKey,
    metaKey: event.metaKey,
    selectionStart: input.selectionStart ?? 0,
    selectionEnd: input.selectionEnd ?? 0,
    value: input.value,
  };

  if (
    shouldRecallPreviousAgentComposerHistory(keyEvent) &&
    (sharedHistory.value.length > 0 ||
      Boolean(readStoredAgentComposerHistory(sharedHistoryWorkspaceId.value).length))
  ) {
    event.preventDefault();
    stepSharedHistory('previous');
    return true;
  }

  if (shouldRecallNextAgentComposerHistory(keyEvent, sharedHistoryIndex.value >= 0)) {
    event.preventDefault();
    stepSharedHistory('next');
    return true;
  }

  return false;
}
