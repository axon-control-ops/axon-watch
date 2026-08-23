import type { AutonomyReceipt } from '../api/autonomy-api';
import type { LeadPlanRecord } from '../api/lead-plans-api';
import type { WorkspaceTaskRecord } from '../api/tasks-api';
import type { CompanyRosterSnapshot } from '../contracts/canonical';
import { employeeStatusIsActivelyBusy } from '../features/workspace-agents/company-roster-status';
import type { FleetHealthGridCell } from './operator-fleet-health-view';

export type WorkspaceDetailOverview = {
  workspaceId: string;
  label: string;
  health: 'nominal' | 'attention' | 'critical';
  summary: string;
  isBoundProject: boolean;
  projectRoot: string | null;
  employeeCount: number;
  busyCount: number;
};

export function buildWorkspaceDetailOverview(
  workspaceId: string,
  cell: FleetHealthGridCell | null,
  company: CompanyRosterSnapshot | null,
): WorkspaceDetailOverview {
  const roster = company?.company ?? null;
  const employees = roster?.employees ?? [];
  return {
    workspaceId,
    label: cell?.label ?? roster?.display_name ?? workspaceId,
    health: cell?.health ?? 'nominal',
    summary: cell?.summary ?? 'Nominal',
    isBoundProject: cell?.isBoundProject ?? false,
    projectRoot: roster?.project_root ?? null,
    employeeCount: roster?.employee_count ?? employees.length,
    busyCount: employees.filter((employee) => employeeStatusIsActivelyBusy(employee.status)).length,
  };
}

export type WorkspaceNextAction = {
  id: string;
  label: string;
  detail: string;
  ownerRole: string;
  kind: 'plan' | 'task';
};

const OPEN_TASK_STATUSES = new Set(['open', 'leased']);

/** Highest-signal work still outstanding: the active plan first, then open/leased tasks. */
export function buildWorkspaceNextActions(
  tasks: WorkspaceTaskRecord[],
  plans: LeadPlanRecord[],
  maxItems = 8,
): WorkspaceNextAction[] {
  const actions: WorkspaceNextAction[] = [];

  const activePlan = plans.find((plan) => plan.status === 'active' || plan.status === 'awaiting_engagement');
  if (activePlan) {
    actions.push({
      id: `plan:${activePlan.plan_id}`,
      label: activePlan.awaiting_engagement ? 'Lead plan awaiting engagement' : 'Lead plan active',
      detail: activePlan.goal,
      ownerRole: 'lead',
      kind: 'plan',
    });
  }

  const openTasks = tasks
    .filter((task) => OPEN_TASK_STATUSES.has(task.status))
    .sort((left, right) => (right.updated_at || '').localeCompare(left.updated_at || ''));

  for (const task of openTasks) {
    if (actions.length >= maxItems) {
      break;
    }
    actions.push({
      id: `task:${task.task_id}`,
      label: task.status === 'leased' ? 'In progress' : 'Queued',
      detail: task.goal,
      ownerRole: task.owner_role,
      kind: 'task',
    });
  }

  return actions.slice(0, maxItems);
}

export type WorkspaceLogEntry = {
  id: string;
  createdAt: string;
  kind: string;
  tier: string;
  risk: string;
  title: string;
  detail: string;
  status: string;
  needsOperator: boolean;
};

/** Full pending+recent autonomy receipt log for a workspace, newest first. */
export function buildWorkspaceLogEntries(
  pendingDecisions: AutonomyReceipt[],
  recentReceipts: AutonomyReceipt[],
): WorkspaceLogEntry[] {
  const byId = new Map<string, AutonomyReceipt>();
  for (const receipt of [...pendingDecisions, ...recentReceipts]) {
    byId.set(receipt.receipt_id, receipt);
  }
  return Array.from(byId.values())
    .sort((left, right) => (right.created_at || '').localeCompare(left.created_at || ''))
    .map((receipt) => ({
      id: receipt.receipt_id,
      createdAt: receipt.created_at,
      kind: receipt.kind,
      tier: receipt.tier,
      risk: receipt.risk,
      title: receipt.title,
      detail: receipt.detail,
      status: receipt.status,
      needsOperator: receipt.ask_operator && receipt.status === 'pending',
    }));
}
