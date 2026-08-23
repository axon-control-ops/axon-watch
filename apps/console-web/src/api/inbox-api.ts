import type { InboxItem } from '../contracts/canonical';

import { fetchJson, fetchWithTimeout, INBOX_FETCH_TIMEOUT_MS } from './client';

export interface InboxSnapshot {
  items: InboxItem[];
  count: number;
  updated_at: string;
}

export interface AcknowledgeInboxSignalsResult {
  accepted: boolean;
  acknowledged: string[];
  count: number;
  command_id?: string;
  status?: string;
}

export async function fetchInbox(options?: { force?: boolean }): Promise<InboxSnapshot> {
  const path = options?.force ? '/api/inbox?force=true' : '/api/inbox';
  return fetchJson<InboxSnapshot>(
    path,
    {},
    'inbox request failed',
    INBOX_FETCH_TIMEOUT_MS,
  );
}

export type EmailFolderRole = 'inbox' | 'sent' | 'junk' | 'archive' | 'trash' | 'drafts';

export interface EmailFoldersResult {
  account_id: string;
  folders: Partial<Record<EmailFolderRole, string>>;
}

export interface EmailFolderMessage {
  uid: string;
  message_id: string;
  subject: string;
  from: string;
  text: string;
  snippet: string;
  sent_at: string;
  account_id: string;
  account_email: string;
}

export interface EmailMessagesResult {
  account_id: string;
  role: string;
  items: EmailFolderMessage[];
  count: number;
}

export async function fetchEmailFolders(workspaceId: string): Promise<EmailFoldersResult> {
  return fetchJson<EmailFoldersResult>(
    `/api/email/folders?workspace_id=${encodeURIComponent(workspaceId)}`,
    {},
    'email folders request failed',
    INBOX_FETCH_TIMEOUT_MS,
  );
}

export async function fetchEmailMessages(
  workspaceId: string,
  role: EmailFolderRole,
  options?: { limit?: number },
): Promise<EmailMessagesResult> {
  const params = new URLSearchParams({ workspace_id: workspaceId, role });
  if (options?.limit) {
    params.set('limit', String(options.limit));
  }
  return fetchJson<EmailMessagesResult>(
    `/api/email/messages?${params.toString()}`,
    {},
    'email messages request failed',
    INBOX_FETCH_TIMEOUT_MS,
  );
}

async function acknowledgeInboxSignalsViaWatchCommand(
  signalIds: string[],
): Promise<AcknowledgeInboxSignalsResult> {
  const response = await fetchWithTimeout('/api/watch/commands', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      command_type: 'acknowledge_signal',
      target_type: 'signal',
      requested_by: 'operator',
      payload: { signal_ids: signalIds },
    }),
  });

  if (!response.ok) {
    if (response.status === 400 || response.status === 503) {
      throw new Error(
        'Signal clear is unavailable until services restart: ./scripts/dev/down.sh && ./scripts/dev/up.sh',
      );
    }
    throw new Error(`signal acknowledge request failed with status ${response.status}`);
  }

  const payload = (await response.json()) as {
    accepted?: boolean;
    command_id?: string;
    status?: string;
    receipt?: {
      result?: {
        acknowledged?: string[];
        count?: number;
      };
    };
  };
  const result = payload.receipt?.result;
  const acknowledged = Array.isArray(result?.acknowledged) ? result.acknowledged : [];

  return {
    accepted: Boolean(payload.accepted),
    acknowledged,
    count: typeof result?.count === 'number' ? result.count : acknowledged.length,
    command_id: payload.command_id,
    status: payload.status,
  };
}

export async function acknowledgeInboxSignals(
  signalIds: string[],
): Promise<AcknowledgeInboxSignalsResult> {
  const response = await fetchWithTimeout('/api/inbox/signals/acknowledge', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ signal_ids: signalIds }),
  });

  if (response.status === 404) {
    return acknowledgeInboxSignalsViaWatchCommand(signalIds);
  }

  if (!response.ok) {
    throw new Error(`signal acknowledge request failed with status ${response.status}`);
  }

  return response.json() as Promise<AcknowledgeInboxSignalsResult>;
}
