export type WorkspaceMissionStatus =
  | 'planned'
  | 'running'
  | 'blocked'
  | 'verifying'
  | 'ready_for_promotion'
  | 'completed'
  | 'cancelled';

export interface WorkspaceImpactEdge {
  source_workspace_id: string;
  target_workspace_id: string;
  evidence_kind: 'explicit' | 'package_dependency' | 'prior_handoff' | string;
  evidence?: string;
  actionable: boolean;
  confidence: number;
  verification_commands?: string[];
  evidence_globs?: string[];
  promotion_order?: number;
  review_reason?: string;
}

export interface WorkspaceMissionVerification {
  status?: 'pending' | 'passed' | 'failed' | string;
  receipts?: Array<{
    workspace_id: string;
    command: string;
    exit_code: number;
    output: string;
  }>;
}

export interface WorkspaceMissionNode {
  node_id: string;
  mission_id: string;
  workspace_id: string;
  task_id?: string | null;
  owner_role: string;
  relation: 'source' | 'affected' | 'impact_review' | string;
  status: string;
  dependency_task_ids: string[];
  delivery_id?: string | null;
  commit_sha?: string | null;
  draft_pr_url?: string | null;
  delivery_stage?: string | null;
  verification: WorkspaceMissionVerification;
  blocker: string;
  promotion_order: number;
}

export interface WorkspaceMissionPromotion {
  node_id: string;
  workspace_id: string;
  commit_sha?: string | null;
  draft_pr_url?: string | null;
  status: 'approval_required' | 'no_change' | 'promoted' | 'failed' | string;
  detail: string;
}

export interface WorkspaceMissionIntegrationManifest {
  mission_id: string;
  workspaces: Record<string, { commit_sha: string }>;
}

export interface WorkspaceMission {
  mission_id: string;
  dedupe_key: string;
  goal: string;
  status: WorkspaceMissionStatus;
  risk: string;
  source_workspace_id: string;
  source_task_id?: string | null;
  source_run_id?: string | null;
  impact: WorkspaceImpactEdge[];
  integration_manifest: WorkspaceMissionIntegrationManifest | Record<string, never>;
  promotions: WorkspaceMissionPromotion[];
  blocker: string;
  nodes: WorkspaceMissionNode[];
  created_at: string;
  updated_at: string;
}
