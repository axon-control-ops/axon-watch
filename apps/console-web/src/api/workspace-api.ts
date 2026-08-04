import type {
  WorkspaceRecord,
  WorkspaceAgentListSnapshot,
  WorkspaceAgentRecord,
  CompanyRosterSnapshot,
} from '../contracts/canonical';

import { fetchJson, apiUrl } from './client';

export interface WorkspaceListSnapshot {
  items: WorkspaceRecord[];
  count: number;
}

export interface CreateWorkspaceHandoffRequest {
  target_workspace_id: string;
  task: string;
  reason?: string;
}

export interface WorkspaceHandoffCreateResponse {
  handoff: Record<string, unknown>;
  target_workspace: WorkspaceRecord;
  target_workspace_summary: Record<string, unknown>;
  target_task_id?: string | null;
  routed_role?: string;
  communication_thread_id?: string | null;
}

export interface WorkspaceHandoffListSnapshot {
  items: Array<Record<string, unknown>>;
  count: number;
}

export interface WorkspaceFileEntry {
  path: string;
  size_bytes: number;
}

export interface WorkspaceFileListSnapshot {
  workspace_id: string;
  items: WorkspaceFileEntry[];
  count: number;
}

export interface WorkspaceFileContent {
  workspace_id: string;
  path: string;
  content: string;
  size_bytes: number;
}

export interface WorkspaceFileRenameResponse {
  workspace_id: string;
  old_path: string;
  path: string;
  size_bytes: number;
  renamed: boolean;
}

export interface TerminalSessionRecord {
  session_id: string;
  workspace_id: string;
  role: 'operator' | 'agent' | string;
  title: string;
  run_id: string | null;
  created_at: string;
}

function encodeWorkspaceFilePath(filePath: string): string {
  return filePath
    .split('/')
    .map((segment) => encodeURIComponent(segment))
    .join('/');
}

export function resolveWorkspaceFileRawUrl(workspaceId: string, filePath: string): string {
  const encodedWorkspaceId = encodeURIComponent(workspaceId);
  const encodedPath = encodeWorkspaceFilePath(filePath.replace(/^\/+/, ''));
  return apiUrl(`/api/workspaces/${encodedWorkspaceId}/files/${encodedPath}/raw`);
}

export async function createWorkspaceHandoff(
  sourceWorkspaceId: string,
  body: CreateWorkspaceHandoffRequest,
): Promise<WorkspaceHandoffCreateResponse> {
  const encoded = encodeURIComponent(sourceWorkspaceId);
  return fetchJson<WorkspaceHandoffCreateResponse>(
    `/api/workspaces/${encoded}/handoffs`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    'workspace handoff failed',
  );
}

export async function listWorkspaceHandoffs(
  workspaceId: string,
): Promise<WorkspaceHandoffListSnapshot> {
  const encoded = encodeURIComponent(workspaceId);
  return fetchJson<WorkspaceHandoffListSnapshot>(
    `/api/workspaces/${encoded}/handoffs`,
    {},
    'workspace handoffs request failed',
  );
}

export async function fetchWorkspaces(options?: {
  scope?: 'all' | 'operator';
}): Promise<WorkspaceListSnapshot> {
  const scope = options?.scope === 'operator' ? 'operator' : '';
  const query = scope ? '?scope=operator' : '';
  return fetchJson<WorkspaceListSnapshot>(
    `/api/workspaces${query}`,
    {},
    'workspaces request failed',
  );
}

export interface RegisterWorkspaceBindingRequest {
  workspace_id: string;
  project_root: string;
  display_name?: string | null;
}

export interface RegisterWorkspaceBindingResponse {
  workspace: WorkspaceRecord;
  created: boolean;
}

export async function registerWorkspaceBinding(
  body: RegisterWorkspaceBindingRequest,
): Promise<RegisterWorkspaceBindingResponse> {
  return fetchJson<RegisterWorkspaceBindingResponse>(
    '/api/workspaces',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workspace_id: body.workspace_id,
        project_root: body.project_root,
        display_name: body.display_name ?? null,
      }),
    },
    'workspace register failed',
  );
}

export async function fetchWorkspace(workspaceId: string): Promise<WorkspaceRecord> {
  return fetchJson<WorkspaceRecord>(
    `/api/workspaces/${workspaceId}`,
    {},
    'workspace request failed',
  );
}

export type WorkspaceComposerPrefs = {
  workspace_id: string;
  cursor_cli_model: string;
  runtime_target: string;
  updated_at: string | null;
};

export async function fetchWorkspaceComposerPrefs(
  workspaceId: string,
): Promise<WorkspaceComposerPrefs> {
  const encoded = encodeURIComponent(workspaceId);
  return fetchJson<WorkspaceComposerPrefs>(
    `/api/workspaces/${encoded}/composer-prefs`,
    {},
    'workspace composer prefs request failed',
  );
}

export async function saveWorkspaceComposerPrefs(
  workspaceId: string,
  body: { cursor_cli_model?: string; runtime_target?: string },
): Promise<WorkspaceComposerPrefs> {
  const encoded = encodeURIComponent(workspaceId);
  return fetchJson<WorkspaceComposerPrefs>(
    `/api/workspaces/${encoded}/composer-prefs`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    'workspace composer prefs save failed',
  );
}

export async function fetchWorkspaceAgents(options?: {
  scope?: 'all' | 'operator';
}): Promise<WorkspaceAgentListSnapshot> {
  const scope = options?.scope === 'operator' ? 'operator' : '';
  const query = scope ? '?scope=operator' : '';
  return fetchJson<WorkspaceAgentListSnapshot>(
    `/api/agents${query}`,
    {},
    'workspace agents request failed',
  );
}

export async function fetchWorkspaceAgent(workspaceId: string): Promise<WorkspaceAgentRecord> {
  const encoded = encodeURIComponent(workspaceId);
  return fetchJson<WorkspaceAgentRecord>(
    `/api/workspaces/${encoded}/agent`,
    {},
    'workspace agent request failed',
  );
}

export async function fetchWorkspaceCompany(workspaceId: string): Promise<CompanyRosterSnapshot> {
  const encoded = encodeURIComponent(workspaceId);
  return fetchJson<CompanyRosterSnapshot>(
    `/api/workspaces/${encoded}/company`,
    {},
    'workspace company request failed',
  );
}

export async function fetchWorkspaceFiles(workspaceId: string): Promise<WorkspaceFileListSnapshot> {
  const encoded = encodeURIComponent(workspaceId);
  return fetchJson<WorkspaceFileListSnapshot>(
    `/api/workspaces/${encoded}/files`,
    {},
    'workspace files request failed',
  );
}

export async function fetchWorkspaceFile(
  workspaceId: string,
  filePath: string,
): Promise<WorkspaceFileContent> {
  const encodedWorkspace = encodeURIComponent(workspaceId);
  const encodedPath = encodeWorkspaceFilePath(filePath);
  return fetchJson<WorkspaceFileContent>(
    `/api/workspaces/${encodedWorkspace}/files/${encodedPath}`,
    {},
    'workspace file read failed',
  );
}

export async function saveWorkspaceFile(
  workspaceId: string,
  filePath: string,
  content: string,
): Promise<{ saved: boolean; path: string; size_bytes: number }> {
  const encodedWorkspace = encodeURIComponent(workspaceId);
  const encodedPath = encodeWorkspaceFilePath(filePath);
  return fetchJson<{ saved: boolean; path: string; size_bytes: number }>(
    `/api/workspaces/${encodedWorkspace}/files/${encodedPath}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    },
    'workspace file save failed',
  );
}

export async function renameWorkspaceFile(
  workspaceId: string,
  filePath: string,
  newPath: string,
): Promise<WorkspaceFileRenameResponse> {
  const encodedWorkspace = encodeURIComponent(workspaceId);
  const encodedPath = encodeWorkspaceFilePath(filePath);
  return fetchJson<WorkspaceFileRenameResponse>(
    `/api/workspaces/${encodedWorkspace}/files/${encodedPath}/rename`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_path: newPath }),
    },
    'workspace file rename failed',
  );
}

export async function fetchWorkspaceTerminalSessions(
  workspaceId: string,
): Promise<{ workspace_id: string; items: TerminalSessionRecord[]; count: number }> {
  const encodedWorkspaceId = encodeURIComponent(workspaceId);
  return fetchJson<{ workspace_id: string; items: TerminalSessionRecord[]; count: number }>(
    `/api/workspaces/${encodedWorkspaceId}/terminal/sessions`,
    {},
    'workspace terminal sessions failed',
  );
}

export async function createWorkspaceTerminalSession(
  workspaceId: string,
  options: {
    role?: 'operator' | 'agent' | string;
    title?: string | null;
    runId?: string | null;
    sessionId?: string | null;
  } = {},
): Promise<TerminalSessionRecord> {
  const encodedWorkspaceId = encodeURIComponent(workspaceId);
  return fetchJson<TerminalSessionRecord>(
    `/api/workspaces/${encodedWorkspaceId}/terminal/sessions`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        role: options.role ?? 'operator',
        title: options.title ?? null,
        run_id: options.runId ?? null,
        session_id: options.sessionId ?? null,
      }),
    },
    'workspace terminal session create failed',
  );
}

export async function renameWorkspaceTerminalSession(
  workspaceId: string,
  sessionId: string,
  title: string,
): Promise<TerminalSessionRecord> {
  const encodedWorkspaceId = encodeURIComponent(workspaceId);
  const encodedSessionId = encodeURIComponent(sessionId);
  return fetchJson<TerminalSessionRecord>(
    `/api/workspaces/${encodedWorkspaceId}/terminal/sessions/${encodedSessionId}/rename`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    },
    'workspace terminal session rename failed',
  );
}

export async function deleteWorkspaceTerminalSession(
  workspaceId: string,
  sessionId: string,
): Promise<{ workspace_id: string; deleted: boolean; items: TerminalSessionRecord[]; count: number }> {
  const encodedWorkspaceId = encodeURIComponent(workspaceId);
  const encodedSessionId = encodeURIComponent(sessionId);
  return fetchJson<{
    workspace_id: string;
    deleted: boolean;
    items: TerminalSessionRecord[];
    count: number;
  }>(
    `/api/workspaces/${encodedWorkspaceId}/terminal/sessions/${encodedSessionId}`,
    { method: 'DELETE' },
    'workspace terminal session delete failed',
  );
}

export type AgentTerminalJobRecord = {
  job_id: string;
  workspace_id: string;
  session_id: string;
  run_id: string | null;
  command: string;
  status: string;
  created_at: string;
  receipt: string;
  stream_to_chat?: boolean;
  thread_id?: string | null;
  message_id?: string | null;
  agent_terminal_session: TerminalSessionRecord;
};

export async function enqueueWorkspaceAgentTerminalJob(
  workspaceId: string,
  options: {
    command: string;
    run_id?: string | null;
    stream_to_chat?: boolean | null;
    thread_id?: string | null;
    message_id?: string | null;
  },
): Promise<AgentTerminalJobRecord> {
  const encodedWorkspaceId = encodeURIComponent(workspaceId);
  return fetchJson<AgentTerminalJobRecord>(
    `/api/workspaces/${encodedWorkspaceId}/terminal/agent-jobs`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        command: options.command,
        run_id: options.run_id ?? null,
        stream_to_chat: options.stream_to_chat ?? null,
        thread_id: options.thread_id ?? null,
        message_id: options.message_id ?? null,
      }),
    },
    'workspace agent terminal job enqueue failed',
  );
}
