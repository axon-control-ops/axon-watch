export const OPERATOR_WORKSPACE_SELECTION_KEY = 'axon-x-operator-workspace';

export function readStoredOperatorWorkspaceId(): string | null {
  if (typeof sessionStorage === 'undefined') {
    return null;
  }

  const raw = sessionStorage.getItem(OPERATOR_WORKSPACE_SELECTION_KEY)?.trim();
  return raw ? raw : null;
}

export function persistOperatorWorkspaceId(workspaceId: string | null): void {
  if (typeof sessionStorage === 'undefined') {
    return;
  }

  if (workspaceId) {
    sessionStorage.setItem(OPERATOR_WORKSPACE_SELECTION_KEY, workspaceId);
    return;
  }

  sessionStorage.removeItem(OPERATOR_WORKSPACE_SELECTION_KEY);
}
