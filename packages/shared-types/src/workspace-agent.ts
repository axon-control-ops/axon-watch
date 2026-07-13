export const WORKSPACE_AGENT_ROLES = ['workspace_agent', 'overview_agent'] as const;
export type WorkspaceAgentRole = (typeof WORKSPACE_AGENT_ROLES)[number];

export const WORKSPACE_AGENT_STATUSES = [
  'idle',
  'watching',
  'planning',
  'executing',
  'verifying',
  'blocked',
  'waiting_approval',
  'handoff_ready',
] as const;
export type WorkspaceAgentStatus = (typeof WORKSPACE_AGENT_STATUSES)[number];

export interface WorkspaceAgentRecord {
  agent_id: string;
  workspace_id: string;
  agent_name: string;
  agent_key: string;
  role: WorkspaceAgentRole;
  status: WorkspaceAgentStatus;
  owns: string;
  enabled: boolean;
  display_name?: string;
  project_root?: string;
}

export interface WorkspaceAgentListSnapshot {
  items: WorkspaceAgentRecord[];
  count: number;
}
