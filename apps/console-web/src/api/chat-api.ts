import type { RunRecord } from '../contracts/canonical';

import type { ChatUiAction } from '../lib/chat-ui-action';

import {
  apiUrl,
  CHAT_MESSAGE_FETCH_TIMEOUT_MS,
  controlPlaneBaseUrl,
  fetchJson,
  THREAD_HISTORY_FETCH_TIMEOUT_MS,
} from './client';
import type { TerminalSessionRecord } from './workspace-api';

export interface ChatAttachmentRecord {
  attachment_id: string;
  workspace_id: string;
  message_id?: string | null;
  thread_id?: string | null;
  filename: string;
  mime_type: string;
  url: string;
  created_at: string;
}

export interface ChatMessageRecord {
  message_id: string;
  thread_id: string;
  run_id: string | null;
  workspace_id: string | null;
  role: 'operator' | 'system' | string;
  content: string;
  created_at: string;
  attachments?: ChatAttachmentRecord[];
}

export interface EditorSelectionContext {
  file_path: string;
  start_line: number;
  end_line: number;
  text: string;
}

export interface PostChatMessageRequest {
  workspace_id: string;
  content: string;
  thread_id?: string | null;
  run_id?: string | null;
  composer_mode?: 'ask' | 'plan' | 'agent' | 'debug' | 'command' | string | null;
  active_file_path?: string | null;
  editor_selection?: EditorSelectionContext | null;
  terminal_snippet?: string | null;
  attachment_ids?: string[] | null;
  runtime_target?: string | null;
  runtime_model?: string | null;
  execution_access?: 'consultative' | 'full' | string | null;
  kairo_session_id?: string | null;
}

export interface PostChatMessageResponse {
  thread_id: string;
  messages: ChatMessageRecord[];
  run_id: string;
  dispatched: boolean;
  run: RunRecord | null;
  streaming?: boolean;
  stream_agent_message_id?: string;
  ui_action?: ChatUiAction | null;
  agent_terminal_session?: TerminalSessionRecord | null;
}

export interface WorkspaceChatThreadListItem {
  thread_id: string;
  workspace_id: string;
  run_id: string | null;
  thread_kind: string;
  title?: string | null;
  employee_id?: string | null;
  employee_role?: string | null;
  created_at: string;
  updated_at: string;
  preview_label: string;
}

export interface WorkspaceChatThreadListSnapshot {
  workspace_id: string;
  thread_kind: string;
  items: WorkspaceChatThreadListItem[];
  count: number;
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

export function resolveChatAttachmentUrl(url: string): string {
  const normalized = String(url ?? '').trim();
  if (!normalized) {
    return '';
  }
  if (/^https?:\/\//i.test(normalized)) {
    return normalized;
  }
  const baseUrl = controlPlaneBaseUrl();
  if (!baseUrl) {
    return normalized;
  }
  return normalized.startsWith('/') ? `${baseUrl}${normalized}` : `${baseUrl}/${normalized}`;
}

export function hasWorkspaceChatThread(
  snapshot: WorkspaceChatThreadSnapshot,
): snapshot is WorkspaceChatThreadSnapshot & { thread_id: string } {
  return snapshot.thread_id !== null;
}

export async function postChatMessage(body: PostChatMessageRequest): Promise<PostChatMessageResponse> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (String(body.execution_access ?? '').trim().toLowerCase() === 'full') {
    // Gate 2 residual: remote surfaces require this step-up header with Full Access.
    headers['X-Axon-Step-Up'] = 'full-access';
  }
  return fetchJson<PostChatMessageResponse>(
    '/api/chat/messages',
    {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    },
    'chat message submit failed',
    CHAT_MESSAGE_FETCH_TIMEOUT_MS,
  );
}

export async function fetchThreadHistory(threadId: string): Promise<ThreadHistorySnapshot> {
  const encodedThreadId = encodeURIComponent(threadId);
  return fetchJson<ThreadHistorySnapshot>(
    `/api/chat/threads/${encodedThreadId}/history`,
    {},
    'thread history fetch failed',
    THREAD_HISTORY_FETCH_TIMEOUT_MS,
  );
}

export async function fetchWorkspaceChatThread(
  workspaceId: string,
  options: { surface?: 'operator' | 'ide' } = {},
): Promise<WorkspaceChatThreadSnapshot> {
  const encodedWorkspaceId = encodeURIComponent(workspaceId);
  const surface = options.surface ?? 'operator';
  const query = `?surface=${encodeURIComponent(surface)}`;
  return fetchJson<WorkspaceChatThreadSnapshot>(
    `/api/workspaces/${encodedWorkspaceId}/chat/thread${query}`,
    {},
    'workspace chat thread lookup failed',
  );
}

export async function uploadChatAttachment(
  workspaceId: string,
  file: File,
): Promise<ChatAttachmentRecord> {
  const formData = new FormData();
  formData.append('workspace_id', workspaceId);
  formData.append('file', file, file.name);

  const response = await fetch(apiUrl('/api/chat/attachments'), {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`chat attachment upload failed with status ${response.status}`);
  }

  return response.json() as Promise<ChatAttachmentRecord>;
}

export async function fetchWorkspaceChatThreads(
  workspaceId: string,
  options: { surface?: 'operator' | 'ide'; limit?: number } = {},
): Promise<WorkspaceChatThreadListSnapshot> {
  const encodedWorkspaceId = encodeURIComponent(workspaceId);
  const surface = options.surface ?? 'ide';
  const limit = options.limit ?? 25;
  const query = `?surface=${encodeURIComponent(surface)}&limit=${encodeURIComponent(String(limit))}`;
  return fetchJson<WorkspaceChatThreadListSnapshot>(
    `/api/workspaces/${encodedWorkspaceId}/chat/threads${query}`,
    {},
    'workspace chat thread list failed',
  );
}

export async function createWorkspaceChatThread(
  workspaceId: string,
  options: {
    surface?: 'operator' | 'ide';
    runId?: string | null;
    title?: string | null;
    employeeId?: string | null;
    employeeRole?: string | null;
  } = {},
): Promise<WorkspaceChatThreadListItem> {
  const encodedWorkspaceId = encodeURIComponent(workspaceId);
  return fetchJson<WorkspaceChatThreadListItem>(
    `/api/workspaces/${encodedWorkspaceId}/chat/threads`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        surface: options.surface ?? 'ide',
        run_id: options.runId ?? null,
        title: options.title ?? null,
        employee_id: options.employeeId ?? null,
        employee_role: options.employeeRole ?? null,
      }),
    },
    'workspace chat thread create failed',
  );
}
