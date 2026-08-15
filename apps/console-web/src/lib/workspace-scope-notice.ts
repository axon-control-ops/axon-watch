import { ref } from 'vue';

export type WorkspaceScopeNotice = {
  currentWorkspaceId: string;
  inferredWorkspaceId: string;
  inferredLabel: string;
  currentLabel: string;
  pendingDraft: string;
};

/** Blocks send until the operator switches workspace or dismisses. */
export const workspaceScopeNotice = ref<WorkspaceScopeNotice | null>(null);

export function setWorkspaceScopeNotice(notice: WorkspaceScopeNotice | null): void {
  workspaceScopeNotice.value = notice;
}

export function clearWorkspaceScopeNotice(): void {
  workspaceScopeNotice.value = null;
}
