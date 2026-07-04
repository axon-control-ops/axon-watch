import type { OperatorBriefing } from '../contracts/canonical';

export type BriefingPanelLoadState = 'idle' | 'loading' | 'loaded' | 'error';
export type BriefingConnectivity = OperatorBriefing['connectivity'];

export function briefingPanelHeadline(
  briefing: OperatorBriefing | null,
  loadState: BriefingPanelLoadState,
): string {
  if (loadState === 'loading') {
    return 'Loading OperatorBriefing';
  }

  if (loadState === 'error') {
    return 'OperatorBriefing unavailable';
  }

  if (!briefing) {
    return 'Awaiting OperatorBriefing';
  }

  if (briefing.pending_approvals.count > 0) {
    return `${briefing.pending_approvals.count} pending approval(s)`;
  }

  const primarySignal = briefing.top_signals[0];
  if (primarySignal) {
    return primarySignal.title;
  }

  if (!briefing.connectivity.watch_connected) {
    return 'Watch disconnected';
  }

  if (briefing.degraded.active) {
    return 'Runtime degraded';
  }

  return 'Systems nominal';
}

export function briefingHasActions(briefing: OperatorBriefing | null): boolean {
  return Boolean(briefing && briefing.next_safe_actions.length > 0);
}

export function briefingHasTopSignals(briefing: OperatorBriefing | null): boolean {
  return Boolean(briefing && briefing.top_signals.length > 0);
}

export function briefingConnectivityLabels(connectivity: BriefingConnectivity): string[] {
  return [
    connectivity.control_plane_ready ? 'Control plane ready' : 'Control plane not ready',
    connectivity.watch_connected ? 'Watch connected' : 'Watch disconnected',
  ];
}

export function briefingIsEmpty(briefing: OperatorBriefing | null): boolean {
  if (!briefing) {
    return true;
  }

  return (
    briefing.pending_approvals.count === 0 &&
    briefing.next_safe_actions.length === 0 &&
    briefing.top_signals.length === 0 &&
    !briefing.degraded.active &&
    briefing.connectivity.control_plane_ready &&
    briefing.connectivity.watch_connected
  );
}
