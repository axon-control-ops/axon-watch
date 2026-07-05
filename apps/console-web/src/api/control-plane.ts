import type {
  InboxItem,
  OperatorBriefing,
  RunRecord,
  RuntimeSummary,
  WorkspaceRecord,
} from '../contracts/canonical';

import type { RunHistorySnapshot } from '../lib/run-history-view';

export interface InboxSnapshot {
  items: InboxItem[];
  count: number;
  updated_at: string;
}

export interface RunListSnapshot {
  items: RunRecord[];
  count: number;
}

export interface WorkspaceListSnapshot {
  items: WorkspaceRecord[];
  count: number;
}

export interface CreateRunRequest {
  workspace_id: string;
  mode?: RunRecord['mode'];
  summary: string;
  detail?: string;
  requires_approval?: boolean;
}

function controlPlaneBaseUrl(): string {
  const configured = import.meta.env.VITE_CONTROL_PLANE_BASE_URL;
  if (configured) {
    return configured.replace(/\/$/, '');
  }

  return '';
}

export async function fetchRuntimeSummary(): Promise<RuntimeSummary> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runtime/summary` : '/api/runtime/summary';
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`runtime summary request failed with status ${response.status}`);
  }

  return response.json() as Promise<RuntimeSummary>;
}

export async function fetchInbox(): Promise<InboxSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/inbox` : '/api/inbox';
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`inbox request failed with status ${response.status}`);
  }

  return response.json() as Promise<InboxSnapshot>;
}

export async function fetchOperatorBriefing(options?: {
  viewportCompact?: boolean;
}): Promise<OperatorBriefing> {
  const baseUrl = controlPlaneBaseUrl();
  const compact =
    options?.viewportCompact ??
    (typeof window !== 'undefined' ? window.innerWidth < 768 : false);
  const query = compact ? '?viewport_compact=true' : '';
  const url = baseUrl ? `${baseUrl}/api/briefing${query}` : `/api/briefing${query}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`operator briefing request failed with status ${response.status}`);
  }

  return response.json() as Promise<OperatorBriefing>;
}

export async function fetchRuns(): Promise<RunListSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runs` : '/api/runs';
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`runs request failed with status ${response.status}`);
  }

  return response.json() as Promise<RunListSnapshot>;
}

export async function fetchWorkspaces(): Promise<WorkspaceListSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/workspaces` : '/api/workspaces';
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`workspaces request failed with status ${response.status}`);
  }

  return response.json() as Promise<WorkspaceListSnapshot>;
}

export async function fetchWorkspace(workspaceId: string): Promise<WorkspaceRecord> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/workspaces/${workspaceId}` : `/api/workspaces/${workspaceId}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`workspace request failed with status ${response.status}`);
  }

  return response.json() as Promise<WorkspaceRecord>;
}

export async function fetchRun(runId: string): Promise<RunRecord> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runs/${runId}` : `/api/runs/${runId}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`run request failed with status ${response.status}`);
  }

  return response.json() as Promise<RunRecord>;
}

export async function fetchRunHistory(runId: string): Promise<RunHistorySnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const encodedRunId = encodeURIComponent(runId);
  const url = baseUrl
    ? `${baseUrl}/api/runs/${encodedRunId}/history`
    : `/api/runs/${encodedRunId}/history`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`run history request failed with status ${response.status}`);
  }

  return response.json() as Promise<RunHistorySnapshot>;
}

export async function createRun(body: CreateRunRequest): Promise<RunRecord> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runs` : '/api/runs';
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`create run request failed with status ${response.status}`);
  }

  return response.json() as Promise<RunRecord>;
}

export async function completeRun(runId: string): Promise<RunRecord> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runs/${runId}/complete` : `/api/runs/${runId}/complete`;
  const response = await fetch(url, { method: 'POST' });

  if (!response.ok) {
    throw new Error(`complete run request failed with status ${response.status}`);
  }

  return response.json() as Promise<RunRecord>;
}

export async function markRunReviewReady(runId: string): Promise<RunRecord> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runs/${runId}/review-ready` : `/api/runs/${runId}/review-ready`;
  const response = await fetch(url, { method: 'POST' });

  if (!response.ok) {
    throw new Error(`review-ready request failed with status ${response.status}`);
  }

  return response.json() as Promise<RunRecord>;
}

export async function stopRun(runId: string): Promise<RunRecord> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runs/${runId}/stop` : `/api/runs/${runId}/stop`;
  const response = await fetch(url, { method: 'POST' });

  if (!response.ok) {
    throw new Error(`stop run request failed with status ${response.status}`);
  }

  return response.json() as Promise<RunRecord>;
}

export async function resumeRun(runId: string): Promise<RunRecord> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runs/${runId}/resume` : `/api/runs/${runId}/resume`;
  const response = await fetch(url, { method: 'POST' });

  if (!response.ok) {
    throw new Error(`resume run request failed with status ${response.status}`);
  }

  return response.json() as Promise<RunRecord>;
}

export async function approveRun(runId: string): Promise<RunRecord> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runs/${runId}/approve` : `/api/runs/${runId}/approve`;
  const response = await fetch(url, { method: 'POST' });

  if (!response.ok) {
    throw new Error(`approve run request failed with status ${response.status}`);
  }

  return response.json() as Promise<RunRecord>;
}

export async function rejectRun(runId: string): Promise<RunRecord> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/runs/${runId}/reject` : `/api/runs/${runId}/reject`;
  const response = await fetch(url, { method: 'POST' });

  if (!response.ok) {
    throw new Error(`reject run request failed with status ${response.status}`);
  }

  return response.json() as Promise<RunRecord>;
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

export async function fetchWorkspaceFiles(workspaceId: string): Promise<WorkspaceFileListSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const encoded = encodeURIComponent(workspaceId);
  const url = baseUrl
    ? `${baseUrl}/api/workspaces/${encoded}/files`
    : `/api/workspaces/${encoded}/files`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`workspace files request failed with status ${response.status}`);
  }

  return response.json() as Promise<WorkspaceFileListSnapshot>;
}

export async function fetchWorkspaceFile(
  workspaceId: string,
  filePath: string,
): Promise<WorkspaceFileContent> {
  const baseUrl = controlPlaneBaseUrl();
  const encodedWorkspace = encodeURIComponent(workspaceId);
  const encodedPath = filePath
    .split('/')
    .map((segment) => encodeURIComponent(segment))
    .join('/');
  const url = baseUrl
    ? `${baseUrl}/api/workspaces/${encodedWorkspace}/files/${encodedPath}`
    : `/api/workspaces/${encodedWorkspace}/files/${encodedPath}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`workspace file read failed with status ${response.status}`);
  }

  return response.json() as Promise<WorkspaceFileContent>;
}

export async function saveWorkspaceFile(
  workspaceId: string,
  filePath: string,
  content: string,
): Promise<{ saved: boolean; path: string; size_bytes: number }> {
  const baseUrl = controlPlaneBaseUrl();
  const encodedWorkspace = encodeURIComponent(workspaceId);
  const encodedPath = filePath
    .split('/')
    .map((segment) => encodeURIComponent(segment))
    .join('/');
  const url = baseUrl
    ? `${baseUrl}/api/workspaces/${encodedWorkspace}/files/${encodedPath}`
    : `/api/workspaces/${encodedWorkspace}/files/${encodedPath}`;
  const response = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });

  if (!response.ok) {
    throw new Error(`workspace file save failed with status ${response.status}`);
  }

  return response.json() as Promise<{ saved: boolean; path: string; size_bytes: number }>;
}

export async function renameWorkspaceFile(
  workspaceId: string,
  filePath: string,
  newPath: string,
): Promise<WorkspaceFileRenameResponse> {
  const baseUrl = controlPlaneBaseUrl();
  const encodedWorkspace = encodeURIComponent(workspaceId);
  const encodedPath = filePath
    .split('/')
    .map((segment) => encodeURIComponent(segment))
    .join('/');
  const url = baseUrl
    ? `${baseUrl}/api/workspaces/${encodedWorkspace}/files/${encodedPath}/rename`
    : `/api/workspaces/${encodedWorkspace}/files/${encodedPath}/rename`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ new_path: newPath }),
  });

  if (!response.ok) {
    throw new Error(`workspace file rename failed with status ${response.status}`);
  }

  return response.json() as Promise<WorkspaceFileRenameResponse>;
}

export interface ChatMessageRecord {
  message_id: string;
  thread_id: string;
  run_id: string | null;
  workspace_id: string | null;
  role: 'operator' | 'system' | string;
  content: string;
  created_at: string;
}

export interface PostChatMessageRequest {
  workspace_id: string;
  content: string;
  thread_id?: string | null;
  run_id?: string | null;
}

export interface PostChatMessageResponse {
  thread_id: string;
  messages: ChatMessageRecord[];
  run_id: string;
  dispatched: boolean;
  run: RunRecord;
}

export interface ThreadHistorySnapshot {
  thread_id: string;
  workspace_id: string;
  run_id: string | null;
  items: ChatMessageRecord[];
  count: number;
}

export interface WorkspaceChatThreadSnapshot {
  thread_id: string | null;
  workspace_id: string;
  run_id: string | null;
  updated_at: string | null;
}

export function hasWorkspaceChatThread(
  snapshot: WorkspaceChatThreadSnapshot,
): snapshot is WorkspaceChatThreadSnapshot & { thread_id: string } {
  return snapshot.thread_id !== null;
}

export async function postChatMessage(
  body: PostChatMessageRequest,
): Promise<PostChatMessageResponse> {
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/chat/messages` : '/api/chat/messages';
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`chat message submit failed with status ${response.status}`);
  }

  return response.json() as Promise<PostChatMessageResponse>;
}

export async function fetchThreadHistory(threadId: string): Promise<ThreadHistorySnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const encodedThreadId = encodeURIComponent(threadId);
  const url = baseUrl
    ? `${baseUrl}/api/chat/threads/${encodedThreadId}/history`
    : `/api/chat/threads/${encodedThreadId}/history`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`thread history fetch failed with status ${response.status}`);
  }

  return response.json() as Promise<ThreadHistorySnapshot>;
}

export async function fetchWorkspaceChatThread(
  workspaceId: string,
): Promise<WorkspaceChatThreadSnapshot> {
  const baseUrl = controlPlaneBaseUrl();
  const encodedWorkspaceId = encodeURIComponent(workspaceId);
  const url = baseUrl
    ? `${baseUrl}/api/workspaces/${encodedWorkspaceId}/chat/thread`
    : `/api/workspaces/${encodedWorkspaceId}/chat/thread`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`workspace chat thread lookup failed with status ${response.status}`);
  }

  return response.json() as Promise<WorkspaceChatThreadSnapshot>;
}
