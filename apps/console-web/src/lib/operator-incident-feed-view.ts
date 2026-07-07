import type { InboxItem } from '../contracts/canonical';

import type { FleetHealthSnapshot } from '../api/control-plane';

export type OperatorIncidentFeedItem = {
  id: string;
  title: string;
  summary: string;
  severity: 'info' | 'high' | 'critical' | string;
  source: 'signal' | 'fleet';
  workspaceId: string | null;
};

export type OperatorIncidentFeedView = {
  items: OperatorIncidentFeedItem[];
  headline: string;
  emptyCopy: string;
};

const SEVERITY_RANK: Record<string, number> = {
  critical: 0,
  high: 1,
  info: 2,
};

function severityRank(severity: string): number {
  return SEVERITY_RANK[severity] ?? 3;
}

export function buildOperatorIncidentFeed(input: {
  topSignals: InboxItem[];
  workspaceId: string | null;
  fleetHealth: FleetHealthSnapshot | null;
  limit?: number;
}): OperatorIncidentFeedView {
  const limit = input.limit ?? 5;
  const items: OperatorIncidentFeedItem[] = [];
  const seen = new Set<string>();

  for (const signal of input.topSignals) {
    if (
      input.workspaceId &&
      signal.workspace_id &&
      signal.workspace_id !== input.workspaceId
    ) {
      continue;
    }
    if (seen.has(signal.signal_id)) {
      continue;
    }
    seen.add(signal.signal_id);
    items.push({
      id: signal.signal_id,
      title: signal.title,
      summary: signal.summary?.trim() || 'Open signal needs review.',
      severity: signal.severity,
      source: 'signal',
      workspaceId: signal.workspace_id ?? null,
    });
  }

  if (input.fleetHealth && input.workspaceId) {
    const row = input.fleetHealth.items.find(
      (entry) => entry.workspace_id === input.workspaceId,
    );
    if (
      row?.top_signal_title &&
      row.open_signals_count > 0 &&
      !items.some((item) => item.title === row.top_signal_title)
    ) {
      items.push({
        id: `fleet-${row.workspace_id}`,
        title: row.top_signal_title,
        summary: `${row.open_signals_count} open signal(s) on ${row.display_name}.`,
        severity: row.critical_signals_count > 0 ? 'critical' : 'high',
        source: 'fleet',
        workspaceId: row.workspace_id,
      });
    }
  }

  const sorted = items.sort(
    (left, right) => severityRank(left.severity) - severityRank(right.severity),
  );
  const limited = sorted.slice(0, limit);

  return {
    items: limited,
    headline:
      limited.length > 0
        ? `${limited.length} incident${limited.length === 1 ? '' : 's'} need attention`
        : 'No open incidents in this workspace',
    emptyCopy: 'Signals and monitor events for this workspace will appear here.',
  };
}
