import type { InboxItem, RuntimeSummary } from '../contracts/canonical';

export interface InboxSnapshot {
  items: InboxItem[];
  count: number;
  updated_at: string;
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
