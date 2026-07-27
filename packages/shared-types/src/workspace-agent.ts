export const WORKSPACE_AGENT_ROLES = [
  'lead',
  'watcher',
  'frontend',
  'backend',
  'integrations',
  'workspace_agent',
  'overview_agent',
] as const;
export type WorkspaceAgentRole = (typeof WORKSPACE_AGENT_ROLES)[number];

export const WORKSPACE_AGENT_STATUSES = [
  'idle',
  'watching',
  'assigned',
  'planning',
  'executing',
  'verifying',
  'blocked',
  'waiting_approval',
  'handoff_ready',
] as const;
export type WorkspaceAgentStatus = (typeof WORKSPACE_AGENT_STATUSES)[number];

export const EMPLOYEE_SCHEDULES = ['always_on', 'continuous', 'on_demand'] as const;
export type EmployeeSchedule = (typeof EMPLOYEE_SCHEDULES)[number];

export interface WorkspaceAgentRecord {
  agent_id: string;
  workspace_id: string;
  agent_name: string;
  agent_key: string;
  role: WorkspaceAgentRole | string;
  status: WorkspaceAgentStatus;
  owns: string;
  enabled: boolean;
  schedule?: EmployeeSchedule | string;
  primary?: boolean;
  display_name?: string;
  project_root?: string;
  company_name?: string;
}

export interface WorkspaceAgentListSnapshot {
  items: WorkspaceAgentRecord[];
  count: number;
  scope?: 'all' | 'operator';
}

export interface CompanyRoleCatalogEntry {
  id: string;
  label: string;
  summary: string;
  default_schedule: EmployeeSchedule | string;
}

export interface CompanyEmployeeRecord {
  employee_id: string;
  workspace_id: string;
  name: string;
  role: WorkspaceAgentRole | string;
  role_label: string;
  schedule: EmployeeSchedule | string;
  schedule_label: string;
  status: WorkspaceAgentStatus;
  owns: string;
  enabled: boolean;
  primary: boolean;
  /** Newest role-tagged shift outcome: failed | completed | phase name. */
  last_outcome?: string | null;
  /** Human-readable failure/success detail — never bare FAILED. */
  last_outcome_detail?: string | null;
  last_run_id?: string | null;
  /** Newest non-terminal role-tagged run, when a shift is in progress. */
  active_run_id?: string | null;
  /** Optional Azure neural voice for Talk / teammate TTS (falls back to operator voice). */
  azure_voice_id?: string | null;
  /** Latest worker delivery stage for this role (git/PR/CI pipeline). */
  pipeline_stage?: string | null;
  pipeline_detail?: string | null;
  draft_pr_url?: string | null;
  ci_status?: string | null;
}

export interface CompanyRosterRecord {
  workspace_id: string;
  company_name: string;
  employee_count: number;
  employees: CompanyEmployeeRecord[];
  primary_employee_id: string | null;
  display_name?: string;
  project_root?: string;
}

export interface CompanyRosterSnapshot {
  company: CompanyRosterRecord;
  role_catalog: CompanyRoleCatalogEntry[];
}
