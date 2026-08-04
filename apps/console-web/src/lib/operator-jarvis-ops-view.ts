import type {
  BriefingAction,
  CompanyEmployeeRecord,
  OperatorBriefing,
  RunRecord,
  RuntimeSummaryActiveRun,
} from '../contracts/canonical';
import type { IdeComposerActivity } from './agent-dock-activity-view';
import type { WorkspaceTaskRecord } from '../api/tasks-api';
import { formatRunDisplayName } from './run-display';
import { runPhaseTag } from './mockup-shell-view';

export type JarvisOpsCardKind = 'run' | 'poll' | 'command' | 'agent' | 'task';

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
  activity: {
    state: 'active' | 'queued' | 'quiet';
    label: string;
    detail: string;
  };
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
  workspaceTasks?: WorkspaceTaskRecord[];
  workspaceNamesById?: Record<string, string>;
};

function truncateAtWord(text: string, maxLen: number): string {
  const cleaned = text.trim();
  if (cleaned.length <= maxLen) {
    return cleaned;
  }
  const candidate = cleaned.slice(0, Math.max(1, maxLen - 1)).trimEnd();
  const boundary = candidate.lastIndexOf(' ');
  return `${(boundary > 0 ? candidate.slice(0, boundary) : candidate).replace(/[ ,;:–—-]+$/, '')}…`;
}

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

  const composerActivity = input.ideComposerActivity;
  if (composerActivity?.label?.trim() || input.agentStreamActive) {
    const live =
      composerActivity?.liveBodyFull?.trim()
      || composerActivity?.label?.trim()
      || 'Agent stream active';
    cards.push({
      id: 'poll:composer',
      kind: 'poll',
      title: input.agentStreamActive ? 'Agent polling / streaming' : 'Composer activity',
      detail: truncateAtWord(live, 160),
      meta: composerActivity?.mode ? composerActivity.mode.toUpperCase() : null,
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

  const activeTasks = (input.workspaceTasks ?? [])
    .filter((task) => task.status === 'open' || task.status === 'leased')
    .sort((left, right) => {
      if (left.status !== right.status) {
        return left.status === 'leased' ? -1 : 1;
      }
      return String(right.updated_at).localeCompare(String(left.updated_at));
    });
  for (const task of activeTasks.slice(0, 6)) {
    const workspace =
      input.workspaceNamesById?.[task.workspace_id] || task.workspace_id.replace(/^workspace_/, '');
    const working = task.status === 'leased';
    cards.push({
      id: `task:${task.task_id}`,
      kind: 'task',
      title: `VAXON ${working ? 'working' : 'queued'} · ${task.owner_role || 'task'}`,
      detail: truncateAtWord(task.goal || 'Task goal unavailable', 180),
      meta: `${working ? 'ACTIVE NOW' : 'QUEUED NEXT'} · ${workspace}`,
      tone: working ? 'info' : 'nominal',
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
  const taskCount = cards.filter((card) => card.kind === 'task').length;
  const workingTasks = activeTasks.filter((task) => task.status === 'leased');
  const queuedTasks = activeTasks.filter((task) => task.status === 'open');
  const workingWorkspaceNames = Array.from(
    new Set(
      workingTasks.map(
        (task) =>
          input.workspaceNamesById?.[task.workspace_id]
          || task.workspace_id.replace(/^workspace_/, ''),
      ),
    ),
  );
  const opsActivity: JarvisOpsView['activity'] = workingTasks.length
    ? {
        state: 'active',
        label: `VAXON ACTIVE · ${workingTasks.length} task${workingTasks.length === 1 ? '' : 's'} in progress`,
        detail: `Working now in ${workingWorkspaceNames.join(', ')}${
          queuedTasks.length
            ? ` · ${queuedTasks.length} queued next`
            : ''
        }`,
      }
    : queuedTasks.length
      ? {
          state: 'queued',
          label: `VAXON READY · ${queuedTasks.length} task${queuedTasks.length === 1 ? '' : 's'} queued`,
          detail: 'Waiting tasks are visible below and will start when their assigned agent is available.',
        }
      : {
          state: 'quiet',
          label: 'VAXON STANDBY',
          detail: 'No VAXON-owned task is actively running or queued.',
        };
  const headline =
    cards.length === 0
      ? 'Mission quiet — no active runs, polls, or agent work'
      : `${runCount} run${runCount === 1 ? '' : 's'} · ${agentCount} agent${agentCount === 1 ? '' : 's'} · ${taskCount} VAXON task${taskCount === 1 ? '' : 's'}`;

  return {
    headline,
    activity: opsActivity,
    cards: cards.slice(0, 12),
  };
}
