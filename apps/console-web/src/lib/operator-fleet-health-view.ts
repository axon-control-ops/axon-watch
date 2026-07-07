import type { WorkspaceRecord } from '../contracts/canonical';

export type FleetHealthTone = 'nominal' | 'attention' | 'critical';

export type FleetHealthWorkspaceRow = {
  workspace_id: string;
  display_name: string;
  connection_kind: string;
  health: FleetHealthTone;
  active_runs: number;
  review_ready_count: number;
  executing_count: number;
  pending_approvals_count: number;
  open_signals_count: number;
  critical_signals_count: number;
  top_signal_title: string | null;
};

export type FleetHealthSnapshot = {
  generated_at: string;
  watch_connected: boolean;
  connectors: {
    configured: number;
    ok: number;
    degraded: number;
    unavailable: number;
    required_unavailable: number;
    last_updated_at?: string;
  };
  degraded: {
    active: boolean;
    reasons: string[];
  };
  items: FleetHealthWorkspaceRow[];
  count: number;
};

export type FleetHealthGridCell = {
  workspaceId: string;
  label: string;
  health: FleetHealthTone;
  summary: string;
  detail: string;
  isSelected: boolean;
  isBoundProject: boolean;
};

const PRODUCTION_WORKSPACE_ORDER = [
  'workspace_axon_watch',
  'workspace_axon_local',
  'workspace_dashpro',
] as const;

export function sortFleetHealthRows(
  rows: FleetHealthWorkspaceRow[],
  workspaces: WorkspaceRecord[],
): FleetHealthWorkspaceRow[] {
  const boundIds = new Set(
    workspaces.filter((item) => item.connection_kind === 'project_path').map((item) => item.workspace_id),
  );
  const priority = new Map<string, number>();
  for (const [index, workspaceId] of PRODUCTION_WORKSPACE_ORDER.entries()) {
    priority.set(workspaceId, index);
  }

  return [...rows].sort((left, right) => {
    const leftBound = boundIds.has(left.workspace_id) ? 0 : 1;
    const rightBound = boundIds.has(right.workspace_id) ? 0 : 1;
    if (leftBound !== rightBound) {
      return leftBound - rightBound;
    }

    const leftPriority = priority.get(left.workspace_id) ?? 99;
    const rightPriority = priority.get(right.workspace_id) ?? 99;
    if (leftPriority !== rightPriority) {
      return leftPriority - rightPriority;
    }

    if (left.health !== right.health) {
      const toneRank: Record<FleetHealthTone, number> = {
        critical: 0,
        attention: 1,
        nominal: 2,
      };
      return toneRank[left.health] - toneRank[right.health];
    }

    return left.display_name.localeCompare(right.display_name);
  });
}

export function buildFleetHealthGridCells(input: {
  snapshot: FleetHealthSnapshot | null;
  workspaces: WorkspaceRecord[];
  selectedWorkspaceId: string | null;
  maxRows?: number;
}): FleetHealthGridCell[] {
  if (!input.snapshot) {
    return [];
  }

  const boundIds = new Set(
    input.workspaces
      .filter((item) => item.connection_kind === 'project_path')
      .map((item) => item.workspace_id),
  );
  const sorted = sortFleetHealthRows(input.snapshot.items, input.workspaces);
  const limit = input.maxRows ?? 12;

  return sorted.slice(0, limit).map((row) => {
    const parts: string[] = [];
    if (row.open_signals_count > 0) {
      parts.push(`${row.open_signals_count} signal${row.open_signals_count === 1 ? '' : 's'}`);
    }
    if (row.review_ready_count > 0) {
      parts.push(`${row.review_ready_count} review`);
    }
    if (row.executing_count > 0) {
      parts.push(`${row.executing_count} running`);
    }
    if (row.pending_approvals_count > 0) {
      parts.push(`${row.pending_approvals_count} approval`);
    }

    const summary = parts.length > 0 ? parts.join(' · ') : 'Nominal';
    const detail = row.top_signal_title?.trim() || row.workspace_id;

    return {
      workspaceId: row.workspace_id,
      label: row.display_name,
      health: row.health,
      summary,
      detail,
      isSelected: row.workspace_id === input.selectedWorkspaceId,
      isBoundProject: boundIds.has(row.workspace_id),
    };
  });
}

export function fleetHealthHeadline(snapshot: FleetHealthSnapshot | null): string {
  if (!snapshot) {
    return 'Loading fleet health…';
  }

  const attention = snapshot.items.filter((row) => row.health !== 'nominal').length;
  if (attention === 0) {
    return `${snapshot.count} workspace${snapshot.count === 1 ? '' : 's'} · systems nominal`;
  }

  return `${attention} workspace${attention === 1 ? '' : 's'} need attention · ${snapshot.connectors.ok}/${snapshot.connectors.configured} connectors ok`;
}
