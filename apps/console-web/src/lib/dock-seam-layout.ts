import type { LayoutMode } from '../stores/shell';
import type { OperatorBriefing } from '../contracts/canonical';

export type DockSeamId =
  | 'briefing'
  | 'approvals'
  | 'signals'
  | 'run'
  | 'thread'
  | 'command';

export interface DockSeamLayoutState {
  id: DockSeamId;
  title: string;
  hero: boolean;
  collapsed: boolean;
  compactSummary: string | null;
}

export function briefingCoversApprovals(briefing: OperatorBriefing | null): boolean {
  return Boolean(briefing && briefing.pending_approvals.count > 0);
}

export function briefingCoversSignals(briefing: OperatorBriefing | null): boolean {
  return Boolean(briefing && briefing.top_signals.length > 0);
}

export function briefingHasInterruptiveSignals(briefing: OperatorBriefing | null): boolean {
  return Boolean(
    briefing?.top_signals.some(
      (signal) => signal.severity === 'high' || signal.severity === 'critical',
    ),
  );
}

export function briefingCoversActiveRun(briefing: OperatorBriefing | null): boolean {
  return Boolean(briefing && briefing.active_runs.length > 0);
}

export function buildDockSeamLayout(input: {
  layoutMode: LayoutMode;
  briefing: OperatorBriefing | null;
  approvalsSummary: string;
  signalsSummary: string;
  runSummary: string;
  threadSummary: string;
  expandedSeams: Set<DockSeamId>;
}): DockSeamLayoutState[] {
  const operatorMode = input.layoutMode === 'operator';
  const coversApprovals = briefingCoversApprovals(input.briefing);
  const interruptiveSignals = briefingHasInterruptiveSignals(input.briefing);
  const coversRun = briefingCoversActiveRun(input.briefing);

  const seams: DockSeamLayoutState[] = [
    {
      id: 'briefing',
      title: 'KAIRO Briefing',
      hero: operatorMode,
      collapsed: false,
      compactSummary: null,
    },
    {
      id: 'approvals',
      title: 'Approvals',
      hero: false,
      collapsed: operatorMode && coversApprovals && !input.expandedSeams.has('approvals'),
      compactSummary: input.approvalsSummary,
    },
    {
      id: 'signals',
      title: 'Signals',
      hero: false,
      collapsed:
        operatorMode && interruptiveSignals && !input.expandedSeams.has('signals'),
      compactSummary: input.signalsSummary,
    },
    {
      id: 'run',
      title: 'Active Run',
      hero: !operatorMode,
      collapsed: operatorMode && coversRun && !input.expandedSeams.has('run'),
      compactSummary: input.runSummary,
    },
    {
      id: 'thread',
      title: 'Conversation',
      hero: operatorMode,
      collapsed: !input.expandedSeams.has('thread'),
      compactSummary: input.threadSummary,
    },
    {
      id: 'command',
      title: 'Command',
      hero: false,
      collapsed: operatorMode && !input.expandedSeams.has('command'),
      compactSummary: 'Operator command entry',
    },
  ];

  if (operatorMode) {
    return seams;
  }

  return seams.map((seam) => ({
    ...seam,
    hero: seam.id === 'run',
    collapsed: seam.id === 'briefing' && !input.expandedSeams.has('briefing'),
  }));
}
