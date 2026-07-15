import type { BriefingAction, OperatorBriefing, RunRecord } from '../../contracts/canonical';
import {
  briefingAdvise,
  briefingConnectivityLabels,
  briefingNotice,
  briefingPanelHeadline,
  type BriefingPanelLoadState,
} from '../../lib/briefing-panel-view';
import { runPhaseTag } from '../../lib/mockup-shell-view';
import type { GalaxyPresencePhase } from './galaxy-presence-state';

export type GalaxyIntelligenceChip = {
  id: string;
  label: string;
  tone: 'nominal' | 'attention' | 'critical' | 'info';
};

export type GalaxyIntelligenceView = {
  headline: string;
  notice: string;
  advise: string;
  presencePhase: GalaxyPresencePhase;
  runPhaseLabel: string | null;
  approvalCount: number;
  criticalSignals: number;
  highSignals: number;
  safeActions: BriefingAction[];
  connectivityChips: GalaxyIntelligenceChip[];
  degradedReasons: string[];
  workspaceLabel: string | null;
  topSignalTitles: string[];
  routingReceipt: string | null;
};

export type GalaxyIntelligenceInput = {
  briefing: OperatorBriefing | null;
  briefingLoadState: BriefingPanelLoadState;
  primaryActiveRun: Pick<RunRecord, 'run_id' | 'summary' | 'detail' | 'phase'> | null;
  presencePhase: GalaxyPresencePhase;
  workspaceLabel: string | null;
  routingReceipt?: string | null;
};

export function projectGalaxyIntelligence(
  input: GalaxyIntelligenceInput,
): GalaxyIntelligenceView {
  const briefing = input.briefing;
  const loadState = input.briefingLoadState;
  const criticalSignals =
    briefing?.top_signals.filter((signal) => signal.severity === 'critical').length ?? 0;
  const highSignals =
    briefing?.top_signals.filter((signal) => signal.severity === 'high').length ?? 0;
  const approvalCount = briefing?.pending_approvals.count ?? 0;
  const connectivity = briefing?.connectivity;
  const connectivityChips: GalaxyIntelligenceChip[] = connectivity
    ? briefingConnectivityLabels(connectivity).map((label, index) => ({
        id: `conn-${index}`,
        label,
        tone: label.includes('not ') || label.includes('disconnected') ? 'attention' : 'nominal',
      }))
    : [];

  return {
    headline: briefingPanelHeadline(briefing, loadState),
    notice: briefingNotice(briefing, loadState, {
      primaryActiveRun: input.primaryActiveRun,
    }),
    advise: briefingAdvise(briefing, loadState),
    presencePhase: input.presencePhase,
    runPhaseLabel: input.primaryActiveRun
      ? runPhaseTag(input.primaryActiveRun.phase)
      : null,
    approvalCount,
    criticalSignals,
    highSignals,
    safeActions: (briefing?.next_safe_actions ?? []).slice(0, 4),
    connectivityChips,
    degradedReasons: briefing?.degraded.active ? briefing.degraded.reasons.slice(0, 4) : [],
    workspaceLabel: input.workspaceLabel,
    topSignalTitles: (briefing?.top_signals ?? []).slice(0, 3).map((signal) => signal.title),
    routingReceipt: input.routingReceipt?.trim() || null,
  };
}
