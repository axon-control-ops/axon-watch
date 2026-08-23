export interface ApprovalRecord {
  approval_id: string;
  run_id: string;
  workspace_id: string;
}

export interface WorkspaceRecord {
  workspace_id: string;
  connection_kind?: 'isolated_root' | 'project_path';
  project_root?: string;
  display_name?: string;
  /** True when config/workspace-agents.json has a company for this
   * workspace with at least one enabled employee — i.e. someone is
   * actually staffed to work here right now. */
  has_active_team?: boolean;
}

export interface WorkspaceHandoffRecord {
  handoff_id: string;
  source_workspace_id: string;
  target_workspace_id: string;
  task: string;
  reason: string;
  status: 'recorded' | 'routed' | string;
  target_task_id?: string | null;
  routed_role?: string;
  routed_employee_id?: string;
  communication_thread_id?: string | null;
  source_communication_thread_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceHandoffSummary {
  run_count: number;
  active_run_count: number;
  active_runs: Array<{
    run_id: string;
    status: string;
    phase: string;
    summary: string;
  }>;
}

export interface ThreadMessage {
  message_id: string;
  thread_id: string;
  run_id: string | null;
  workspace_id: string | null;
}
