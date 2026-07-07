import type { WorkspaceRecord } from '../contracts/canonical';

import { workspaceDisplayLabel } from './operator-workspace-catalog';

export function workspacePickerPrimaryLabel(workspace: WorkspaceRecord): string {
  return workspaceDisplayLabel(workspace);
}

/** Secondary line for picker trigger and list rows (path preferred over raw id). */
export function workspacePickerMetaLabel(workspace: WorkspaceRecord): string {
  const root = workspace.project_root?.trim();
  if (root) {
    return shortenWorkspacePath(root);
  }

  const displayName = workspace.display_name?.trim();
  if (displayName && displayName !== workspace.workspace_id) {
    return workspace.workspace_id;
  }

  return '';
}

export function shortenWorkspacePath(path: string): string {
  const normalized = path.replace(/\\/g, '/').replace(/\/+$/, '');
  const parts = normalized.split('/').filter(Boolean);
  if (parts.length <= 2) {
    return normalized.startsWith('/') ? `/${parts.join('/')}` : parts.join('/');
  }

  const tail = parts.slice(-2).join('/');
  return normalized.startsWith('/') ? `/…/${tail}` : `…/${tail}`;
}
