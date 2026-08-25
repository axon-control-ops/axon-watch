import type { WorkspaceRecord } from '../contracts/canonical';

import { canonicalWorkspaceLabel } from './kairo-entity-labels';
import {
  DEFAULT_OPERATOR_WORKSPACE_ID,
  MOCKUP_WORKSPACE_IDS,
  mergeMockupWorkspaceCatalog,
} from './mockup-shell-view';

/** Preferred order when bound project workspaces exist (production operator). */
export const PRODUCTION_OPERATOR_WORKSPACE_IDS = [
  'workspace_axon_watch',
  'workspace_edudashpro_school',
  'workspace_dashpro',
] as const;

export function hasBoundProjectWorkspaces(items: WorkspaceRecord[]): boolean {
  return items.some((item) => item.connection_kind === 'project_path');
}

function isMockupWorkspaceRecord(item: WorkspaceRecord): boolean {
  return MOCKUP_WORKSPACE_IDS.includes(
    item.workspace_id as (typeof MOCKUP_WORKSPACE_IDS)[number],
  );
}

/** True when the API only handed us the legacy demo fleet (or nothing). */
export function isMockupOnlyCatalog(items: WorkspaceRecord[]): boolean {
  return items.length === 0 || items.every(isMockupWorkspaceRecord);
}

export function isProductionOperatorCatalog(items: WorkspaceRecord[]): boolean {
  // Bound roots are definitive. Also treat non-mockup operator IDs as production
  // even when bindings briefly load as isolated_root (packaged CP / cold start).
  return hasBoundProjectWorkspaces(items) || !isMockupOnlyCatalog(items);
}

export function mergeOperatorWorkspaceCatalog(items: WorkspaceRecord[]): WorkspaceRecord[] {
  if (!isProductionOperatorCatalog(items)) {
    return mergeMockupWorkspaceCatalog(items);
  }

  const byId = new Map(items.map((item) => [item.workspace_id, item]));
  const orderedIds: string[] = [];
  const bound = hasBoundProjectWorkspaces(items);

  for (const workspaceId of PRODUCTION_OPERATOR_WORKSPACE_IDS) {
    if (byId.has(workspaceId)) {
      orderedIds.push(workspaceId);
    }
  }

  for (const item of items) {
    // When real project bindings exist, drop stray demo isolated_root rows.
    if (bound && item.connection_kind !== 'project_path') {
      continue;
    }
    if (!orderedIds.includes(item.workspace_id)) {
      orderedIds.push(item.workspace_id);
    }
  }

  return orderedIds.map((workspaceId) => byId.get(workspaceId)!);
}

export function defaultOperatorWorkspaceId(items: WorkspaceRecord[]): string | null {
  if (items.length === 0) {
    return null;
  }

  if (isProductionOperatorCatalog(items)) {
    return (
      items.find((item) => item.workspace_id === 'workspace_axon_watch')?.workspace_id ??
      items[0]?.workspace_id ??
      null
    );
  }

  return (
    items.find((item) => item.workspace_id === DEFAULT_OPERATOR_WORKSPACE_ID)?.workspace_id ??
    items[0]?.workspace_id ??
    DEFAULT_OPERATOR_WORKSPACE_ID
  );
}

export function workspaceDisplayLabel(workspace: WorkspaceRecord): string {
  return canonicalWorkspaceLabel(workspace.workspace_id, workspace.display_name);
}

export function workspaceCatalogMode(items: WorkspaceRecord[]): 'production' | 'mockup' {
  return isProductionOperatorCatalog(items) ? 'production' : 'mockup';
}

export function isCatalogWorkspaceId(
  workspaceId: string | null | undefined,
  catalog: WorkspaceRecord[],
): boolean {
  if (!workspaceId) {
    return false;
  }

  return catalog.some((workspace) => workspace.workspace_id === workspaceId);
}

/** @deprecated mockup-only guard — prefer isCatalogWorkspaceId with the visible catalog */
export function isMockupWorkspaceId(workspaceId: string | null | undefined): boolean {
  if (!workspaceId) {
    return false;
  }

  return MOCKUP_WORKSPACE_IDS.includes(workspaceId as (typeof MOCKUP_WORKSPACE_IDS)[number]);
}
