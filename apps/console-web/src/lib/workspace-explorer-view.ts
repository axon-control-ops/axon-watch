export type WorkspaceFilesLoadState = 'idle' | 'loading' | 'loaded' | 'error';

export function workspaceExplorerStatusMessage(input: {
  loadState: WorkspaceFilesLoadState;
  hasWorkspace: boolean;
  entryCount: number;
  error?: string | null;
}): string | null {
  if (input.loadState === 'loading') {
    return 'Loading workspace files…';
  }
  if (input.loadState === 'error') {
    return input.error?.trim() || 'Workspace files unavailable.';
  }
  if (!input.hasWorkspace) {
    return 'Select a workspace to browse files.';
  }
  if (input.loadState === 'idle') {
    return 'Preparing explorer…';
  }
  return null;
}
