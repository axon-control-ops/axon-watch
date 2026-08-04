export interface SwitchWorkspaceUiAction {
  type: 'switch_workspace';
  workspace_id: string;
  open_file_path?: string | null;
  layout_mode?: 'operator' | 'ide';
  focus_attention?: boolean;
  auto_attend?: boolean;
  signal_id?: string | null;
  cta_label?: string | null;
}

export interface OpenSourceUiAction {
  type: 'open_source';
  workspace_id: string;
  open_file_path: string;
}

export interface HandoffIdeUiAction {
  type: 'handoff_ide';
  signal_id: string;
  target_workspace_id: string;
  task: string;
}

export interface SurfaceArtifactUiAction {
  type: 'surface_artifact';
  artifact_id: string;
}

export interface MoveVoiceOrbUiAction {
  type: 'move_voice_orb';
  dock?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'center';
  mode?: 'smart_dodge';
}

export type ChatUiAction =
  | SwitchWorkspaceUiAction
  | OpenSourceUiAction
  | HandoffIdeUiAction
  | SurfaceArtifactUiAction
  | MoveVoiceOrbUiAction;

export function parseChatUiAction(value: unknown): ChatUiAction | null {
  if (!value || typeof value !== 'object') {
    return null;
  }

  const record = value as Record<string, unknown>;
  if (record.type === 'switch_workspace') {
    const workspaceId = String(record.workspace_id ?? '').trim();
    if (!workspaceId) {
      return null;
    }

    const openFilePath = String(record.open_file_path ?? '').trim();
    const layoutMode = String(record.layout_mode ?? '').trim().toLowerCase();
    const ctaLabel = String(record.cta_label ?? '').trim();
    const signalId = String(record.signal_id ?? '').trim();
    return {
      type: 'switch_workspace',
      workspace_id: workspaceId,
      open_file_path: openFilePath || null,
      layout_mode: layoutMode === 'ide' || layoutMode === 'operator' ? layoutMode : undefined,
      focus_attention: record.focus_attention === true,
      auto_attend: record.auto_attend === true,
      signal_id: signalId || null,
      cta_label: ctaLabel || null,
    };
  }

  if (record.type === 'open_source') {
    const workspaceId = String(record.workspace_id ?? '').trim();
    const openFilePath = String(record.open_file_path ?? '').trim();
    if (!workspaceId || !openFilePath) {
      return null;
    }
    return {
      type: 'open_source',
      workspace_id: workspaceId,
      open_file_path: openFilePath,
    };
  }

  if (record.type === 'handoff_ide') {
    const signalId = String(record.signal_id ?? '').trim();
    const targetWorkspaceId = String(record.target_workspace_id ?? '').trim();
    const task = String(record.task ?? '').trim();
    if (!signalId || !targetWorkspaceId || !task) {
      return null;
    }
    return {
      type: 'handoff_ide',
      signal_id: signalId,
      target_workspace_id: targetWorkspaceId,
      task,
    };
  }

  if (record.type === 'surface_artifact') {
    const artifactId = String(record.artifact_id ?? '').trim();
    if (!artifactId) {
      return null;
    }
    return {
      type: 'surface_artifact',
      artifact_id: artifactId,
    };
  }

  if (record.type === 'move_voice_orb') {
    const mode = String(record.mode ?? '').trim().toLowerCase();
    if (mode === 'smart_dodge') {
      return { type: 'move_voice_orb', mode: 'smart_dodge' };
    }
    const dock = String(record.dock ?? '')
      .trim()
      .toLowerCase()
      .replace(/_/g, '-');
    if (
      dock === 'top-left' ||
      dock === 'top-right' ||
      dock === 'bottom-left' ||
      dock === 'bottom-right' ||
      dock === 'center'
    ) {
      return { type: 'move_voice_orb', dock };
    }
    return { type: 'move_voice_orb', mode: 'smart_dodge' };
  }

  return null;
}

export interface WorkspaceSwitchShell {
  setCurrentWorkspace: (workspaceId: string) => void;
  openWorkspaceFile: (path: string) => Promise<void>;
  setLayoutMode?: (mode: 'operator' | 'ide') => void;
  focusAttentionSidebar?: (signalId?: string | null) => void;
  handoffSignalToIde?: (
    signal: {
      signal_id: string;
      workspace_id: string;
      task?: string;
      title: string;
      summary: string;
    },
    options?: { autoSubmit?: boolean },
  ) => Promise<void>;
  surfaceOperatorArtifact?: (artifactId: string) => void;
  setVoiceOrbDock?: (dock: string) => void;
  requestVoiceOrbSmartDodge?: (options?: { force?: boolean }) => void;
}

export function applyChatUiAction(
  shell: WorkspaceSwitchShell,
  action: ChatUiAction,
): void {
  if (action.type === 'switch_workspace') {
    shell.setCurrentWorkspace(action.workspace_id);
    if (action.layout_mode) {
      shell.setLayoutMode?.(action.layout_mode);
    }
    if (action.focus_attention) {
      shell.focusAttentionSidebar?.(action.signal_id ?? null);
    }
    if (action.open_file_path) {
      void shell.openWorkspaceFile(action.open_file_path);
    }
    return;
  }

  if (action.type === 'open_source') {
    shell.setCurrentWorkspace(action.workspace_id);
    shell.setLayoutMode?.('ide');
    void shell.openWorkspaceFile(action.open_file_path);
    return;
  }

  if (action.type === 'handoff_ide') {
    void shell.handoffSignalToIde?.(
      {
        signal_id: action.signal_id,
        workspace_id: action.target_workspace_id,
        task: action.task,
        title: action.task,
        summary: action.task,
      },
      { autoSubmit: true },
    );
    return;
  }

  if (action.type === 'surface_artifact') {
    shell.surfaceOperatorArtifact?.(action.artifact_id);
    return;
  }

  if (action.type === 'move_voice_orb') {
    if (action.mode === 'smart_dodge') {
      shell.requestVoiceOrbSmartDodge?.({ force: true });
      return;
    }
    if (action.dock) {
      shell.setVoiceOrbDock?.(action.dock);
    }
  }
}
