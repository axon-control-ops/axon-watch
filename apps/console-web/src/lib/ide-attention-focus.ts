import { isBootstrapSummarySignal } from './operator-signal-hints';

export type AttentionFocusLayoutMode = 'operator' | 'ide';

export type AttentionTopSignal = {
  signal_id: string;
  title: string;
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
): string | null {
  if (explicitSignalId?.trim()) {
    return explicitSignalId.trim();
  }

  const bootstrap = topSignals.find((signal) =>
    isBootstrapSummarySignal(signal.signal_id, signal.title),
  );
  if (bootstrap?.signal_id) {
    return bootstrap.signal_id;
  }

  return topSignals.length === 1 ? topSignals[0]?.signal_id ?? null : null;
}
