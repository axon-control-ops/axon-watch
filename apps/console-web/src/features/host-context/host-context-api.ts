import { detectDesktopCapabilities, type DesktopCapabilityFlags } from '../../lib/desktop-capability';
import { fetchJson } from '../../api/client';
import type {
  HostActionReceipt,
  HostArtifactRecord,
  HostCapabilitiesSnapshot,
  OperatorReminderRecord,
} from '../../contracts/canonical';

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  return fetchJson<T>(path, {
    ...init,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  }, `${path} failed`);
}

export function readLocalCapabilities(): DesktopCapabilityFlags {
  return detectDesktopCapabilities();
}

export async function fetchHostCapabilities(): Promise<HostCapabilitiesSnapshot> {
  return jsonFetch<HostCapabilitiesSnapshot>('/api/host/capabilities');
}

export async function fetchHostArtifacts(query = ''): Promise<HostArtifactRecord[]> {
  const qs = query.trim() ? `?query=${encodeURIComponent(query.trim())}` : '';
  const payload = await jsonFetch<{ items: HostArtifactRecord[] }>(`/api/host/artifacts${qs}`);
  return payload.items ?? [];
}

export async function fetchDueReminders(): Promise<OperatorReminderRecord[]> {
  const payload = await jsonFetch<{ items: OperatorReminderRecord[] }>('/api/host/reminders?due_only=true');
  return payload.items ?? [];
}

export async function patchReminder(
  memoryId: string,
  patch: Partial<OperatorReminderRecord>,
): Promise<OperatorReminderRecord> {
  return jsonFetch<OperatorReminderRecord>(`/api/host/reminders/${encodeURIComponent(memoryId)}`, {
    method: 'PATCH',
    body: JSON.stringify(patch),
  });
}

export async function requestHostAction(input: {
  deviceId: string;
  action: string;
  path?: string;
  commandId?: string;
}): Promise<{ accepted: boolean; receipt: HostActionReceipt | null; decision: Record<string, unknown> }> {
  return jsonFetch('/api/host/actions/request', {
    method: 'POST',
    body: JSON.stringify({
      device_id: input.deviceId,
      action: input.action,
      path: input.path,
      command_id: input.commandId ?? '',
    }),
  });
}

export async function pauseHostAwareness(paused: boolean): Promise<Record<string, unknown>> {
  return jsonFetch('/api/host/privacy/pause', {
    method: 'POST',
    body: JSON.stringify({ paused }),
  });
}
