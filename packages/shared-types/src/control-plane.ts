export interface ApprovalRecord {
  approval_id: string;
  run_id: string;
  workspace_id: string;
}

export interface WorkspaceRecord {
  workspace_id: string;
}

export interface ThreadMessage {
  message_id: string;
  thread_id: string;
  run_id: string | null;
  workspace_id: string | null;
}
