export interface SwitchWorkspaceUiAction {
  type: 'switch_workspace';
  workspace_id: string;
  open_file_path?: string | null;
}

export type ChatUiAction = SwitchWorkspaceUiAction;

export function parseChatUiAction(value: unknown): ChatUiAction | null {
  if (!value || typeof value !== 'object') {
    return null;
  }

  const record = value as Record<string, unknown>;
  if (record.type !== 'switch_workspace') {
    return null;
  }

  const workspaceId = String(record.workspace_id ?? '').trim();
  if (!workspaceId) {
    return null;
  }

  const openFilePath = String(record.open_file_path ?? '').trim();
  return {
    type: 'switch_workspace',
    workspace_id: workspaceId,
    open_file_path: openFilePath || null,
  };
}

export interface WorkspaceSwitchShell {
  setCurrentWorkspace: (workspaceId: string) => void;
  openWorkspaceFile: (path: string) => Promise<void>;
}

export function applyChatUiAction(
  shell: WorkspaceSwitchShell,
  action: ChatUiAction,
): void {
  if (action.type === 'switch_workspace') {
    shell.setCurrentWorkspace(action.workspace_id);
    if (action.open_file_path) {
      void shell.openWorkspaceFile(action.open_file_path);
    }
  }
}
