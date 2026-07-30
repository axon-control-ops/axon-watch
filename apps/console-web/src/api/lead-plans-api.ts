import { fetchJson } from './client';

export type LeadPlanStatus =
  | 'active'
  | 'superseded'
  | 'completed'
  | 'cancelled'
  | 'awaiting_engagement';

export type LeadPlanTaskLink = {
  plan_key: string;
  task_id: string;
};

export type LeadPlanRecord = {
  plan_id: string;
  workspace_id: string;
  goal: string;
  mode: string;
  status: LeadPlanStatus | string;
  plan: Record<string, unknown>;
  supersedes_plan_id: string | null;
  created_at: string;
  updated_at: string;
  task_links: LeadPlanTaskLink[];
  task_ids: string[];
  awaiting_engagement: boolean;
};

export type LeadPlansSnapshot = {
  workspace_id: string;
  items: LeadPlanRecord[];
  count: number;
};

export type LeadFanOutInput = {
  goal: string;
  mode?: 'auto' | 'fan_out' | 'sequential';
  create_runs?: boolean;
};

export async function fetchWorkspaceLeadPlans(
  workspaceId: string,
  options: { limit?: number } = {},
): Promise<LeadPlansSnapshot> {
  const encoded = encodeURIComponent(workspaceId);
  const params = new URLSearchParams();
  if (options.limit != null) {
    params.set('limit', String(options.limit));
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : '';
  return fetchJson<LeadPlansSnapshot>(
    `/api/workspaces/${encoded}/lead/plans${suffix}`,
    {},
    'workspace lead plans request failed',
  );
}

export async function fetchLeadPlan(planId: string): Promise<LeadPlanRecord> {
  const encoded = encodeURIComponent(planId);
  return fetchJson<LeadPlanRecord>(
    `/api/lead/plans/${encoded}`,
    {},
    'lead plan request failed',
  );
}

export async function setLeadPlanStatus(
  planId: string,
  status: 'completed' | 'cancelled' | 'awaiting_engagement',
): Promise<LeadPlanRecord> {
  const encoded = encodeURIComponent(planId);
  return fetchJson<LeadPlanRecord>(
    `/api/lead/plans/${encoded}/status`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    },
    'lead plan status update failed',
  );
}

export async function synthesizeLeadPlan(planId: string): Promise<Record<string, unknown>> {
  const encoded = encodeURIComponent(planId);
  return fetchJson<Record<string, unknown>>(
    `/api/lead/plans/${encoded}/synthesize`,
    { method: 'POST' },
    'lead plan synthesize failed',
  );
}

export async function fanOutLeadPlan(
  workspaceId: string,
  input: LeadFanOutInput,
): Promise<Record<string, unknown>> {
  const encoded = encodeURIComponent(workspaceId);
  return fetchJson<Record<string, unknown>>(
    `/api/workspaces/${encoded}/lead/fan-out`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        goal: input.goal,
        mode: input.mode ?? 'auto',
        create_runs: input.create_runs ?? true,
      }),
    },
    'lead plan fan-out failed',
  );
}
