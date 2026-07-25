export interface RunHistoryReceipt {
  type: string;
  summary: string;
}

export interface RunHistoryTransition {
  from_phase: string | null;
  to_phase: string;
  timestamp: string;
  actor: string;
  current_step?: string | null;
  receipt: RunHistoryReceipt;
}

export interface RunHistorySnapshot {
  run_id: string;
  history_ref: string;
  items: RunHistoryTransition[];
  count: number;
}

export interface RunHistoryRow {
  id: string;
  label: string;
  timestamp: string;
}

export function formatRunHistoryRow(
  transition: RunHistoryTransition,
  index: number,
): RunHistoryRow {
  const receipt = transition.receipt;
  const phaseLabel =
    transition.from_phase === null
      ? transition.to_phase
      : `${transition.from_phase} → ${transition.to_phase}`;

  return {
    id: `${transition.timestamp}-${index}`,
    label: receipt.summary || `${receipt.type} · ${phaseLabel}`,
    timestamp: transition.timestamp,
  };
}

export function buildRunHistoryRows(
  snapshot: RunHistorySnapshot | null,
  limit = 4,
): RunHistoryRow[] {
  if (!snapshot || snapshot.items.length === 0) {
    return [];
  }

  return snapshot.items
    .slice(-limit)
    .reverse()
    .map((transition, index) => formatRunHistoryRow(transition, index));
}
