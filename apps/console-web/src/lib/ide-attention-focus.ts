import { isBootstrapSummarySignal } from './operator-signal-hints';

export type AttentionFocusLayoutMode = 'operator' | 'ide';

export type AttentionTopSignal = {
  signal_id: string;
  title: string;
};

export function resolveAttentionFocusScrollTarget(
  layoutMode: AttentionFocusLayoutMode,
): 'dock-seam-signals' | 'ide-attention-panel' {
  return layoutMode === 'ide' ? 'ide-attention-panel' : 'dock-seam-signals';
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
