import type { InboxItem, OperatorAlertExplanation as ServerAlertExplanation } from '../contracts/canonical';

import type { FleetHealthSnapshot } from '../api/control-plane';
import {
  isBootstrapSummarySignal,
  resolveOperatorAlertExplanation,
} from './operator-signal-hints';

export type OperatorIncidentFeedItem = {
  id: string;
  title: string;
  summary: string;
  /** One-line layman "what happened" for the operator. */
  plainWhat: string;
  severity: 'info' | 'high' | 'critical' | string;
  source: 'signal' | 'fleet';
  workspaceId: string | null;
  monitorSignal: boolean;
  meta?: Record<string, unknown> | null;
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

function isMonitorSignal(signal: InboxItem): boolean {
  return String(signal.meta?.signal_family ?? '') === 'child_project_monitor';
}

function incidentSignalRank(signal: InboxItem): number {
  if (isMonitorSignal(signal)) {
    return 0;
  }
  if (isBootstrapSummarySignal(signal.signal_id, signal.title)) {
    return 4;
  }
  return severityRank(signal.severity);
}

/** Collapse inbox twins that share the same operator-facing title. */
function incidentTitleKey(title: string): string {
  return title.trim().toLowerCase().replace(/\s+/g, ' ');
}

export function buildOperatorIncidentFeed(input: {
  topSignals: InboxItem[];
  workspaceId: string | null;
  fleetHealth: FleetHealthSnapshot | null;
  limit?: number;
  serverExplanation?: ServerAlertExplanation | Record<string, unknown> | null;
  serverSignalId?: string | null;
  serverReason?: string | null;
}): OperatorIncidentFeedView {
  const limit = input.limit ?? 5;
  const items: OperatorIncidentFeedItem[] = [];
  const seenIds = new Set<string>();
  const seenTitles = new Set<string>();

  for (const signal of input.topSignals) {
    if (
      input.workspaceId &&
      signal.workspace_id &&
      signal.workspace_id !== input.workspaceId
    ) {
      continue;
    }
    if (seenIds.has(signal.signal_id)) {
      continue;
    }
    const titleKey = incidentTitleKey(signal.title || '');
    if (titleKey && seenTitles.has(titleKey)) {
      continue;
    }
    seenIds.add(signal.signal_id);
    if (titleKey) {
      seenTitles.add(titleKey);
    }
    const explained = resolveOperatorAlertExplanation({
      signalId: signal.signal_id,
      title: signal.title,
      summary: signal.summary,
      meta: signal.meta ?? null,
      serverExplanation: input.serverExplanation,
      serverSignalId: input.serverSignalId,
      serverReason: input.serverReason,
    });
    items.push({
      id: signal.signal_id,
      title: signal.title,
      summary: signal.summary?.trim() || 'Open signal needs review.',
      plainWhat: explained.what,
      severity: signal.severity,
      source: 'signal',
      workspaceId: signal.workspace_id ?? null,
      monitorSignal: isMonitorSignal(signal),
      meta: signal.meta ?? null,
    });
  }

  if (input.fleetHealth && input.workspaceId) {
    const row = input.fleetHealth.items.find(
      (entry) => entry.workspace_id === input.workspaceId,
    );
    const fleetTitleKey = incidentTitleKey(row?.top_signal_title || '');
    if (
      row?.top_signal_title &&
      row.open_signals_count > 0 &&
      fleetTitleKey &&
      !seenTitles.has(fleetTitleKey)
    ) {
      seenTitles.add(fleetTitleKey);
      const explained = resolveOperatorAlertExplanation({
        title: row.top_signal_title,
        summary: `${row.open_signals_count} open signal(s) on ${row.display_name}.`,
        serverExplanation: input.serverExplanation,
        serverSignalId: input.serverSignalId,
        serverReason: input.serverReason,
      });
      items.push({
        id: `fleet-${row.workspace_id}`,
        title: row.top_signal_title,
        summary: `${row.open_signals_count} open signal(s) on ${row.display_name}.`,
        plainWhat: explained.what,
        severity: row.critical_signals_count > 0 ? 'critical' : 'high',
        source: 'fleet',
        workspaceId: row.workspace_id,
        monitorSignal: false,
      });
    }
  }

  const sorted = items.sort((left, right) => {
    if (left.source === 'signal' && right.source === 'signal') {
      const leftSignal = input.topSignals.find((signal) => signal.signal_id === left.id);
      const rightSignal = input.topSignals.find((signal) => signal.signal_id === right.id);
      if (leftSignal && rightSignal) {
        return incidentSignalRank(leftSignal) - incidentSignalRank(rightSignal);
      }
    }
    return severityRank(left.severity) - severityRank(right.severity);
  });
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
