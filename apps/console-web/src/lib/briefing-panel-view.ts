import type { OperatorBriefing, RunRecord } from '../contracts/canonical';

import { formatRunDisplayName, formatRunIdentityLabel } from './run-display';
import { runPhaseTag } from './mockup-shell-view';

export type BriefingPanelLoadState = 'idle' | 'loading' | 'loaded' | 'error';
export type BriefingConnectivity = OperatorBriefing['connectivity'];

export type BriefingNoticeOptions = {
  primaryActiveRun?: Pick<RunRecord, 'run_id' | 'summary' | 'detail' | 'phase'> | null;
};

function isIdleNoRunsNotice(notice: string | undefined): boolean {
  if (!notice?.trim()) {
    return true;
  }
  return /no active runs/i.test(notice);
}

export function briefingPanelHeadline(
  briefing: OperatorBriefing | null,
  loadState: BriefingPanelLoadState,
): string {
  if (loadState === 'loading') {
    return 'Loading briefing…';
  }

  if (loadState === 'error') {
    return 'Briefing unavailable';
  }

  if (!briefing) {
    return 'Awaiting briefing';
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

export function briefingNotice(
  briefing: OperatorBriefing | null,
  loadState: BriefingPanelLoadState,
  options?: BriefingNoticeOptions,
): string {
  if (loadState === 'loading') {
    return 'Standing by while briefing loads.';
  }

  if (loadState === 'error') {
    return 'Briefing unavailable. Check control-plane connectivity.';
  }

  const primaryActiveRun = options?.primaryActiveRun ?? null;
  if (primaryActiveRun && isIdleNoRunsNotice(briefing?.notice)) {
    if (primaryActiveRun.phase === 'review_ready') {
      return `${formatRunDisplayName(primaryActiveRun)} is ready for your review.`;
    }
    return `${formatRunIdentityLabel(primaryActiveRun)} · ${runPhaseTag(primaryActiveRun.phase)}`;
  }

  if (briefing?.notice) {
    return briefing.notice;
  }

  return 'Awaiting briefing.';
}

export function briefingAdvise(
  briefing: OperatorBriefing | null,
  loadState: BriefingPanelLoadState,
): string {
  if (loadState === 'loading') {
    return 'KAIRO will recommend the next safe action once briefing loads.';
  }

  if (loadState === 'error') {
    return 'Review runtime summary and connectivity before continuing.';
  }

  if (briefing?.advise) {
    return briefing.advise;
  }

  return 'Describe the next action in Command.';
}

export function briefingRhythmField(
  briefing: OperatorBriefing | null,
  field: keyof OperatorBriefing['executive_rhythm'],
  loadState: BriefingPanelLoadState,
): string {
  if (loadState === 'loading') {
    return 'Standing by while executive rhythm loads.';
  }

  if (loadState === 'error') {
    return 'Review runtime summary before continuing.';
  }

  const rhythm = briefing?.executive_rhythm;
  if (rhythm?.[field]) {
    return rhythm[field];
  }

  if (field === 'notice') {
    return briefingNotice(briefing, loadState);
  }
  if (field === 'advise') {
    return briefingAdvise(briefing, loadState);
  }

  return '';
}
