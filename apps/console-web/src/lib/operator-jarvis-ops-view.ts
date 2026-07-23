import type {
  BriefingAction,
  CompanyEmployeeRecord,
  OperatorBriefing,
  RunRecord,
  RuntimeSummaryActiveRun,
} from '../contracts/canonical';
import type { IdeComposerActivity } from './agent-dock-activity-view';
import { formatRunDisplayName } from './run-display';
import { runPhaseTag } from './mockup-shell-view';

export type JarvisOpsCardKind = 'run' | 'poll' | 'command' | 'agent';

export type JarvisOpsCard = {
  id: string;
  kind: JarvisOpsCardKind;
  title: string;
  detail: string;
  meta: string | null;
  tone: 'nominal' | 'attention' | 'critical' | 'info';
};

export type JarvisOpsView = {
  headline: string;
  cards: JarvisOpsCard[];
};

export type BuildJarvisOpsViewInput = {
  briefing: OperatorBriefing | null;
  primaryActiveRun: Pick<
    RunRecord,
    'run_id' | 'summary' | 'detail' | 'phase' | 'status' | 'current_step'
  > | null;
  fleetActiveRuns: Array<
    Pick<RuntimeSummaryActiveRun, 'run_id' | 'workspace_id' | 'phase' | 'title'>
  >;
  ideComposerActivity: IdeComposerActivity | null;
  employees: CompanyEmployeeRecord[];
  agentStreamActive: boolean;
};

function toneForPhase(phase: string | null | undefined): JarvisOpsCard['tone'] {
  if (!phase) {
    return 'info';
  }
  if (phase === 'awaiting_approval' || phase === 'review_ready') {
    return 'attention';
  }
  if (phase === 'failed' || phase === 'blocked') {
    return 'critical';
  }
  if (phase === 'executing' || phase === 'planning') {
    return 'info';
  }
  return 'nominal';
}

export function buildJarvisOpsView(input: BuildJarvisOpsViewInput): JarvisOpsView {
  const cards: JarvisOpsCard[] = [];
  const primary = input.primaryActiveRun;

  if (primary) {
    cards.push({
      id: `run:${primary.run_id}`,
      kind: 'run',
      title: formatRunDisplayName(primary) || primary.summary || 'Active run',
      detail: primary.current_step?.trim() || primary.detail?.trim() || `Phase ${runPhaseTag(primary.phase)}`,
      meta: `${runPhaseTag(primary.phase)} · ${primary.status}`,
      tone: toneForPhase(primary.phase),
    });
  }

  for (const run of input.fleetActiveRuns.slice(0, 4)) {
    if (primary && run.run_id === primary.run_id) {
      continue;
    }
    cards.push({
      id: `fleet:${run.run_id}`,
      kind: 'run',
      title: run.title?.trim() || run.run_id,
      detail: `Workspace ${run.workspace_id}`,
      meta: runPhaseTag(run.phase),
      tone: toneForPhase(run.phase),
    });
  }

  const activity = input.ideComposerActivity;
  if (activity?.label?.trim() || input.agentStreamActive) {
    const live = activity?.liveBodyFull?.trim() || activity?.label?.trim() || 'Agent stream active';
    cards.push({
      id: 'poll:composer',
      kind: 'poll',
      title: input.agentStreamActive ? 'Agent polling / streaming' : 'Composer activity',
      detail: live.length > 160 ? `${live.slice(0, 157)}…` : live,
      meta: activity?.mode ? activity.mode.toUpperCase() : null,
      tone: input.agentStreamActive ? 'info' : 'nominal',
    });
  }

  const working = input.employees.filter((row) =>
    ['watching', 'planning', 'executing', 'verifying', 'blocked', 'waiting_approval', 'handoff_ready'].includes(
      String(row.status),
    ),
  );
  for (const employee of working.slice(0, 4)) {
    cards.push({
      id: `agent:${employee.employee_id}`,
      kind: 'agent',
      title: employee.name,
      detail:
        employee.last_outcome_detail?.trim() ||
        employee.owns?.trim() ||
        `${employee.role_label || employee.role} · ${String(employee.status).replace(/_/g, ' ')}`,
      meta: String(employee.status).replace(/_/g, ' '),
      tone:
        employee.status === 'blocked' || employee.status === 'waiting_approval'
          ? 'attention'
          : 'info',
    });
  }

  const actions = (input.briefing?.next_safe_actions ?? []).slice(0, 3) as BriefingAction[];
  for (const action of actions) {
    cards.push({
      id: `cmd:${action.action_id}`,
      kind: 'command',
      title: action.title,
      detail: action.detail?.trim() || action.kind.replace(/_/g, ' '),
      meta: 'Suggested',
      tone: 'nominal',
    });
  }

  const runCount = cards.filter((card) => card.kind === 'run').length;
  const agentCount = cards.filter((card) => card.kind === 'agent').length;
  const headline =
    cards.length === 0
      ? 'Mission quiet — no active runs, polls, or agent work'
      : `${runCount} run${runCount === 1 ? '' : 's'} · ${agentCount} agent${agentCount === 1 ? '' : 's'} in motion`;

  return {
    headline,
    cards: cards.slice(0, 12),
  };
}
