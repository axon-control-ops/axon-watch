import { ref } from 'vue';

export type WorkspaceScopeNotice = {
  currentWorkspaceId: string;
  inferredWorkspaceId: string;
  inferredLabel: string;
  currentLabel: string;
  pendingDraft: string;
};

/** Blocks send until the operator switches workspace, dismisses, or stays. */
export const workspaceScopeNotice = ref<WorkspaceScopeNotice | null>(null);

/**
 * Pairs the operator has explicitly chosen to keep working across.
 * Mentioning another workspace by name is normal in cross-project work; once
 * the operator says "stay here" for a pair, re-prompting is nagging.
 */
const stayHerePairs = ref<Set<string>>(new Set());

function pairKey(currentWorkspaceId: string, inferredWorkspaceId: string): string {
  return `${currentWorkspaceId}>${inferredWorkspaceId}`;
}

export function isWorkspaceScopePairSuppressed(
  currentWorkspaceId: string,
  inferredWorkspaceId: string,
): boolean {
  return stayHerePairs.value.has(pairKey(currentWorkspaceId, inferredWorkspaceId));
}

export function setWorkspaceScopeNotice(notice: WorkspaceScopeNotice | null): void {
  if (
    notice &&
    isWorkspaceScopePairSuppressed(notice.currentWorkspaceId, notice.inferredWorkspaceId)
  ) {
    workspaceScopeNotice.value = null;
    return;
  }
  workspaceScopeNotice.value = notice;
}

export function clearWorkspaceScopeNotice(): void {
  workspaceScopeNotice.value = null;
}

/** Keep working in the current workspace and stop asking about this pair. */
export function stayInCurrentWorkspaceScope(): void {
  const notice = workspaceScopeNotice.value;
  if (notice) {
    stayHerePairs.value.add(pairKey(notice.currentWorkspaceId, notice.inferredWorkspaceId));
  }
  workspaceScopeNotice.value = null;
}

export function resetWorkspaceScopeStayHere(): void {
  stayHerePairs.value = new Set();
}
