/** VAXON Machine CEO — host pulse + safe process kill. */
import { fetchJson } from '../../api/client';


export type MachineProcessRow = {
  pid: number;
  name: string;
  cmdline: string;
  rss_mb: number;
  protected: boolean;
  junk_candidate: boolean;
  auto_killable: boolean;
};

export type MachinePulse = {
  ok: boolean;
  reason?: string;
  generated_at?: string;
  hostname?: string;
  health: {
    memory_percent?: number | null;
    memory_total_mb?: number | null;
    memory_available_mb?: number | null;
    load_1?: number | null;
    load_5?: number | null;
    load_15?: number | null;
  };
  processes: MachineProcessRow[];
  recommendations: Array<{
    pid: number;
    name: string;
    rss_mb: number;
    action: string;
    reason: string;
  }>;
  spoken?: string;
};

export type MachineCeoTick = {
  ok: boolean;
  autonomy_full: boolean;
  pulse: MachinePulse;
  kills: Array<Record<string, unknown>>;
  skipped_kills: Array<Record<string, unknown>>;
  spoken?: string;
};

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

export async function fetchMachinePulse(): Promise<MachinePulse> {
  return jsonFetch<MachinePulse>('/api/host/machine/pulse');
}

export async function runMachineCeoTick(autoKill = true): Promise<MachineCeoTick> {
  return jsonFetch<MachineCeoTick>(
    `/api/host/machine/ceo-tick?auto_kill=${autoKill ? 'true' : 'false'}`,
    { method: 'POST' },
  );
}

export async function killMachineProcess(
  pid: number,
  options?: { auto?: boolean; force?: boolean },
): Promise<Record<string, unknown>> {
  return jsonFetch('/api/host/machine/kill', {
    method: 'POST',
    body: JSON.stringify({
      pid,
      auto: Boolean(options?.auto),
      force: Boolean(options?.force),
    }),
  });
}
