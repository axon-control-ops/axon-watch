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
  /** True when runs or teammates are actively working in this workspace. */
  isBusy: boolean;
  activeRuns: number;
  busyAgents: number;
  openSignals: number;
  criticalSignals: number;
  pendingApprovals: number;
  reviewReady: number;
};

const PRODUCTION_WORKSPACE_ORDER = [
  'workspace_axon_watch',
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

/** Keep fleet card detail to one compact line (API titles can be multi-signal dumps). */
export function compactFleetHealthDetail(
  topSignalTitle: string | null | undefined,
  workspaceId: string,
): string {
  const raw = topSignalTitle?.trim() || workspaceId;
  const firstLine =
    raw
      .split(/\r?\n| · | \| /)
      .map((part) => part.trim())
      .find((part) => part.length > 0) ?? workspaceId;
  if (firstLine.length <= 72) {
    return firstLine;
  }
  return `${firstLine.slice(0, 69).trimEnd()}…`;
}

export function buildFleetHealthGridCells(input: {
  snapshot: FleetHealthSnapshot | null;
  workspaces: WorkspaceRecord[];
  selectedWorkspaceId: string | null;
  maxRows?: number;
  /** Actively busy teammates keyed by workspace_id. */
  busyEmployeeCountByWorkspace?: Record<string, number>;
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
  const limit = Math.max(input.maxRows ?? 24, boundIds.size);
  const selectedId = input.selectedWorkspaceId?.trim() || null;
  const limited = sorted.slice(0, limit);
  if (selectedId && !limited.some((row) => row.workspace_id === selectedId)) {
    const selected = sorted.find((row) => row.workspace_id === selectedId);
    if (selected) {
      if (limited.length === 0) {
        limited.push(selected);
      } else {
        limited.unshift(selected);
        if (limited.length > limit) {
          limited.pop();
        }
      }
    }
  }

  const busyByWorkspace = input.busyEmployeeCountByWorkspace ?? {};

  return limited.map((row) => {
    const busyAgents = Math.max(0, busyByWorkspace[row.workspace_id] ?? 0);
    const parts: string[] = [];
    if (row.active_runs > 0) {
      parts.push(`${row.active_runs} active`);
    }
    if (row.executing_count > 0) {
      parts.push(`${row.executing_count} running`);
    }
    if (busyAgents > 0) {
      parts.push(`${busyAgents} agent${busyAgents === 1 ? '' : 's'} busy`);
    }
    if (row.open_signals_count > 0) {
      parts.push(`${row.open_signals_count} signal${row.open_signals_count === 1 ? '' : 's'}`);
    }
    if (row.review_ready_count > 0) {
      parts.push(`${row.review_ready_count} review`);
    }
    if (row.pending_approvals_count > 0) {
      parts.push(`${row.pending_approvals_count} approval`);
    }

    const isBusy =
      row.active_runs > 0 || row.executing_count > 0 || busyAgents > 0;
    const summary = parts.length > 0 ? parts.join(' · ') : 'Nominal';
    const detail = compactFleetHealthDetail(row.top_signal_title, row.workspace_id);

    return {
      workspaceId: row.workspace_id,
      label: row.display_name,
      health: row.health,
      summary,
      detail,
      isSelected: row.workspace_id === selectedId,
      isBoundProject: boundIds.has(row.workspace_id),
      isBusy,
      activeRuns: row.active_runs,
      busyAgents,
      openSignals: row.open_signals_count,
      criticalSignals: row.critical_signals_count,
      pendingApprovals: row.pending_approvals_count,
      reviewReady: row.review_ready_count,
    };
  });
}

export function fleetHealthHeadline(snapshot: FleetHealthSnapshot | null): string {
  if (!snapshot) {
    return 'Loading fleet health…';
  }

  const activeRuns = snapshot.items.reduce((sum, row) => sum + row.active_runs, 0);
  const executing = snapshot.items.reduce((sum, row) => sum + row.executing_count, 0);
  const inMotion = activeRuns + executing;
  const attention = snapshot.items.filter((row) => row.health !== 'nominal').length;

  if (inMotion > 0 && attention === 0) {
    return `${inMotion} live job${inMotion === 1 ? '' : 's'} · fleet in motion`;
  }
  if (inMotion > 0) {
    return `${inMotion} live · ${attention} need attention · ${snapshot.connectors.ok}/${snapshot.connectors.configured} connectors ok`;
  }
  if (attention === 0) {
    return `${snapshot.count} workspace${snapshot.count === 1 ? '' : 's'} · systems nominal`;
  }

  return `${attention} workspace${attention === 1 ? '' : 's'} need attention · ${snapshot.connectors.ok}/${snapshot.connectors.configured} connectors ok`;
}

/** Headline when company roster busy counts are available (Mission Control). */
export function fleetHealthHeadlineWithCompanyBusy(
  snapshot: FleetHealthSnapshot | null,
  busyAgents: number,
): string {
  const base = fleetHealthHeadline(snapshot);
  if (!snapshot || busyAgents <= 0) {
    return base;
  }
  if (base.includes('fleet in motion') || base.includes('live ·')) {
    return `${busyAgents} agent${busyAgents === 1 ? '' : 's'} busy · ${base}`;
  }
  if (base.includes('systems nominal')) {
    return `${busyAgents} agent${busyAgents === 1 ? '' : 's'} busy · ${snapshot.count} workspace${snapshot.count === 1 ? '' : 's'} live`;
  }
  return `${busyAgents} agent${busyAgents === 1 ? '' : 's'} busy · ${base}`;
}
