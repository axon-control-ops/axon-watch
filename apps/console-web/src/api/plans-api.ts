import { fetchJson } from './client';

export type PlanSummary = {
  plan_id: string;
  workspace_id: string;
  thread_id: string;
  source_message_id: string;
  title: string;
  path: string;
  created_at: string;
  updated_at: string;
};

export type PlanRecord = PlanSummary & {
  content: string;
};

export type PlansListResponse = {
  items: PlanSummary[];
  count: number;
  workspace_id: string;
};

export async function fetchPlans(workspaceId: string): Promise<PlansListResponse> {
  const params = new URLSearchParams({ workspace_id: workspaceId });
  return fetchJson<PlansListResponse>(
    `/api/plans?${params.toString()}`,
    {},
    'plans list request failed',
  );
}

export async function fetchPlan(workspaceId: string, planId: string): Promise<PlanRecord> {
  const params = new URLSearchParams({ workspace_id: workspaceId });
  return fetchJson<PlanRecord>(
    `/api/plans/${encodeURIComponent(planId)}?${params.toString()}`,
    {},
    'plan request failed',
  );
}
