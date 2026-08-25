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

export function applyWorkspacePickerAutoState(
  workspaces: WorkspaceRecord[],
  autoEnabledByWorkspaceId: Record<string, boolean>,
): WorkspaceRecord[] {
  return workspaces.map((workspace) => {
    if (!Object.prototype.hasOwnProperty.call(autoEnabledByWorkspaceId, workspace.workspace_id)) {
      return workspace;
    }
    return {
      ...workspace,
      auto_enabled: autoEnabledByWorkspaceId[workspace.workspace_id],
    };
  });
}

/** Hide workspaces with a known-inactive team, but never hide the currently
 * selected workspace — switching back to it must stay possible even if its
 * team was turned off after the fact. `has_active_team` is optional, so a
 * record that omits it (an older cache, a source that doesn't set it) stays
 * visible rather than being hidden by default. When the backend provides the
 * newer `auto_enabled` flag, that is the source of truth for operator-facing
 * workspace on/off state. */
export function visibleWorkspacePickerEntries(
  workspaces: WorkspaceRecord[],
  currentWorkspaceId: string | null,
): WorkspaceRecord[] {
  return workspaces.filter((workspace) => {
    if (workspace.workspace_id === currentWorkspaceId) {
      return true;
    }
    if (typeof workspace.auto_enabled === 'boolean') {
      return workspace.auto_enabled;
    }
    return workspace.has_active_team !== false;
  });
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
