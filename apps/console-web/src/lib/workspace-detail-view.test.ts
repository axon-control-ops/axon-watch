import { describe, expect, it } from 'vitest';

import type { AutonomyReceipt } from '../api/autonomy-api';
import type { LeadPlanRecord } from '../api/lead-plans-api';
import type { WorkspaceTaskRecord } from '../api/tasks-api';
import type { CompanyRosterSnapshot } from '../contracts/canonical';
import type { FleetHealthGridCell } from './operator-fleet-health-view';
import {
  buildWorkspaceDetailOverview,
  buildWorkspaceLogEntries,
  buildWorkspaceNextActions,
} from './workspace-detail-view';

function cell(overrides: Partial<FleetHealthGridCell> = {}): FleetHealthGridCell {
  return {
    workspaceId: 'workspace_dashpro',
    label: 'DashPro',
    health: 'attention',
    summary: '1 signal',
    detail: 'Cass (watcher) last shift failed',
    isSelected: false,
    isBoundProject: true,
    isBusy: false,
    activeRuns: 0,
    busyAgents: 0,
    openSignals: 1,
    criticalSignals: 0,
    pendingApprovals: 0,
    reviewReady: 0,
    ...overrides,
  };
}

function task(overrides: Partial<WorkspaceTaskRecord> = {}): WorkspaceTaskRecord {
  return {
    task_id: 'task_1',
    workspace_id: 'workspace_dashpro',
    goal: 'Investigate and fix',
    acceptance_criteria: '',
    risk: 'low',
    owner_role: 'watcher',
    dependencies: [],
    status: 'open',
    lease_holder: null,
    lease_expires_at: null,
    attempt_budget: 2,
    attempts_used: 0,
    terminal_outcome: null,
    run_id: null,
    created_at: '2026-08-07T08:00:00Z',
    updated_at: '2026-08-07T08:00:00Z',
    ...overrides,
  };
}

function plan(overrides: Partial<LeadPlanRecord> = {}): LeadPlanRecord {
  return {
    plan_id: 'plan_1',
    workspace_id: 'workspace_dashpro',
    goal: 'Ship the release',
    mode: 'fan_out',
    status: 'active',
    plan: {},
    supersedes_plan_id: null,
    created_at: '2026-08-07T08:00:00Z',
    updated_at: '2026-08-07T08:00:00Z',
    task_links: [],
    task_ids: [],
    awaiting_engagement: false,
    ...overrides,
  };
}

function receipt(overrides: Partial<AutonomyReceipt> = {}): AutonomyReceipt {
  return {
    receipt_id: 'receipt_1',
    workspace_id: 'workspace_dashpro',
    kind: 'operator_blocker',
    decision: 'escalate',
    tier: 'operator_gated',
    risk: 'high',
    title: 'Cass (watcher) last shift failed',
    detail: 'Codex/OpenAI API key was rejected.',
    dedupe_key: 'failed_shift:workspace_dashpro:watcher',
    task_id: null,
    ask_operator: true,
    status: 'pending',
    resolution: '',
    resolved_at: null,
    created_at: '2026-08-07T08:47:00Z',
    ...overrides,
  };
}

describe('buildWorkspaceDetailOverview', () => {
  it('prefers the fleet cell label/health but falls back to the workspace id', () => {
    const overview = buildWorkspaceDetailOverview('workspace_dashpro', cell(), null);
    expect(overview.label).toBe('DashPro');
    expect(overview.health).toBe('attention');
    expect(overview.employeeCount).toBe(0);
  });

  it('reads employee/busy counts from the nested company roster record', () => {
    const company: CompanyRosterSnapshot = {
      company: {
        workspace_id: 'workspace_dashpro',
        company_name: 'DashPro',
        employee_count: 5,
        employees: [
          { employee_id: 'e1', status: 'executing' } as CompanyRosterSnapshot['company']['employees'][number],
          { employee_id: 'e2', status: 'idle' } as CompanyRosterSnapshot['company']['employees'][number],
        ],
        primary_employee_id: 'e1',
        project_root: '/home/edp/Projectx/product/dashpro',
      },
      role_catalog: [],
    };
    const overview = buildWorkspaceDetailOverview('workspace_dashpro', cell(), company);
    expect(overview.employeeCount).toBe(5);
    expect(overview.busyCount).toBe(1);
    expect(overview.projectRoot).toBe('/home/edp/Projectx/product/dashpro');
  });

  it('falls back to workspace id when no fleet cell is loaded yet', () => {
    const overview = buildWorkspaceDetailOverview('workspace_dashpro', null, null);
    expect(overview.label).toBe('workspace_dashpro');
    expect(overview.health).toBe('nominal');
  });
});

describe('buildWorkspaceNextActions', () => {
  it('leads with the active plan, then open/leased tasks newest first', () => {
    const actions = buildWorkspaceNextActions(
      [
        task({ task_id: 't_old', status: 'open', updated_at: '2026-08-07T06:00:00Z' }),
        task({ task_id: 't_new', status: 'leased', updated_at: '2026-08-07T09:00:00Z' }),
        task({ task_id: 't_done', status: 'completed' }),
      ],
      [plan()],
    );
    expect(actions.map((item) => item.id)).toEqual(['plan:plan_1', 'task:t_new', 'task:t_old']);
    expect(actions[1]?.label).toBe('In progress');
    expect(actions[2]?.label).toBe('Queued');
  });

  it('omits completed/failed/cancelled tasks and skips the plan when none is active', () => {
    const actions = buildWorkspaceNextActions(
      [task({ status: 'completed' }), task({ status: 'failed' }), task({ status: 'cancelled' })],
      [plan({ status: 'completed' })],
    );
    expect(actions).toEqual([]);
  });

  it('caps the list at maxItems', () => {
    const tasks = Array.from({ length: 12 }, (_, index) =>
      task({ task_id: `t_${index}`, updated_at: `2026-08-07T0${index % 9}:00:00Z` }),
    );
    const actions = buildWorkspaceNextActions(tasks, [], 5);
    expect(actions).toHaveLength(5);
  });
});

describe('buildWorkspaceLogEntries', () => {
  it('merges pending and recent receipts, de-duplicated by id, newest first', () => {
    const pending = [receipt({ receipt_id: 'r1', created_at: '2026-08-07T08:56:00Z' })];
    const recent = [
      receipt({ receipt_id: 'r1', created_at: '2026-08-07T08:56:00Z' }),
      receipt({ receipt_id: 'r0', created_at: '2026-08-06T20:42:00Z', status: 'resolved', resolution: 'approved' }),
    ];
    const entries = buildWorkspaceLogEntries(pending, recent);
    expect(entries.map((entry) => entry.id)).toEqual(['r1', 'r0']);
  });

  it('flags an entry as needing the operator only while pending and ask_operator', () => {
    const entries = buildWorkspaceLogEntries(
      [receipt({ receipt_id: 'r1', ask_operator: true, status: 'pending' })],
      [receipt({ receipt_id: 'r2', ask_operator: true, status: 'resolved' })],
    );
    const byId = Object.fromEntries(entries.map((entry) => [entry.id, entry]));
    expect(byId.r1?.needsOperator).toBe(true);
    expect(byId.r2?.needsOperator).toBe(false);
  });
});
