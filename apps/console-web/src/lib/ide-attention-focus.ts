import { isBootstrapSummarySignal } from './operator-signal-hints';

export type AttentionFocusLayoutMode = 'operator' | 'ide';

export type AttentionTopSignal = {
  signal_id: string;
  title: string;
  workspace_id?: string | null;
  severity?: string | null;
};

export type AttentionFocusScrollTarget =
  | 'mission-control-attention'
  | 'ide-attention-panel';

export function resolveAttentionFocusScrollTarget(
  layoutMode: AttentionFocusLayoutMode,
): AttentionFocusScrollTarget {
  return layoutMode === 'ide' ? 'ide-attention-panel' : 'mission-control-attention';
}

export function resolveDefaultHighlightedSignalId(
  topSignals: AttentionTopSignal[],
  explicitSignalId?: string | null,
  preferredSignalId?: string | null,
): string | null {
  if (explicitSignalId?.trim()) {
    return explicitSignalId.trim();
  }

  const preferred = preferredSignalId?.trim();
  if (preferred && topSignals.some((signal) => signal.signal_id === preferred)) {
    return preferred;
  }

  const severityRank: Record<string, number> = {
    critical: 4,
    high: 3,
    warning: 2,
    info: 1,
  };
  const actionable = topSignals
    .filter((signal) => !isBootstrapSummarySignal(signal.signal_id, signal.title))
    .map((signal, index) => ({ signal, index }))
    .sort((left, right) => {
      const severityDelta =
        (severityRank[String(right.signal.severity || '').toLowerCase()] ?? 0) -
        (severityRank[String(left.signal.severity || '').toLowerCase()] ?? 0);
      return severityDelta || left.index - right.index;
    });
  if (actionable[0]?.signal.signal_id) {
    return actionable[0].signal.signal_id;
  }

  const bootstrap = topSignals.find((signal) =>
    isBootstrapSummarySignal(signal.signal_id, signal.title),
  );
  if (bootstrap?.signal_id) {
    return bootstrap.signal_id;
  }

  return topSignals[0]?.signal_id ?? null;
}
