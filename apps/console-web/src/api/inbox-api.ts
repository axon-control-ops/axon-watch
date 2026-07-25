import type { InboxItem } from '../contracts/canonical';

import { apiUrl, fetchJson, INBOX_FETCH_TIMEOUT_MS } from './client';

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

export async function fetchInbox(): Promise<InboxSnapshot> {
  return fetchJson<InboxSnapshot>(
    '/api/inbox',
    {},
    'inbox request failed',
    INBOX_FETCH_TIMEOUT_MS,
  );
}

async function acknowledgeInboxSignalsViaWatchCommand(
  signalIds: string[],
): Promise<AcknowledgeInboxSignalsResult> {
  const response = await fetch(apiUrl('/api/watch/commands'), {
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
  const response = await fetch(apiUrl('/api/inbox/signals/acknowledge'), {
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
