import { fetchJson } from './client';

export type LeadPlanMode = 'auto' | 'fan_out' | 'sequential';

export type LeadPlanItem = {
  plan_key: string;
  goal: string;
  owner_role: string;
  acceptance_criteria?: string;
  dependencies?: string[];
  risk?: string;
  exclusive_paths?: string[];
  assignee_name?: string;
  attachment_ids?: string[];
  source_message_id?: string;
  output_artifacts?: string[];
};

export type LeadTaskPlan = {
  goal: string;
  mode: LeadPlanMode;
  items: LeadPlanItem[];
  ordered_keys: string[];
  source_message_id?: string;
};

export type LeadPlanPreviewResponse = {
  workspace_id: string;
  plan: LeadTaskPlan;
  persisted: boolean;
};

export type LeadFanOutResponse = {
  plan_id: string;
  workspace_id: string;
  goal: string;
  mode: LeadPlanMode;
  plan: LeadTaskPlan;
  tasks: Array<Record<string, unknown>>;
  runs: Array<Record<string, unknown>>;
  deferred: Array<Record<string, unknown>>;
  dispatched_runs?: Array<Record<string, unknown>>;
  receipt: Record<string, unknown>;
};

export async function previewLeadPlan(
  workspaceId: string,
  body: {
    goal: string;
    mode?: LeadPlanMode;
    attachment_ids?: string[];
    source_message_id?: string | null;
  },
): Promise<LeadPlanPreviewResponse> {
  const encoded = encodeURIComponent(workspaceId);
  return fetchJson<LeadPlanPreviewResponse>(
    `/api/workspaces/${encoded}/lead/plan`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        goal: body.goal,
        mode: body.mode ?? 'auto',
        persist: false,
        attachment_ids: body.attachment_ids ?? [],
        source_message_id: body.source_message_id ?? null,
      }),
    },
    'lead plan preview failed',
  );
}

export async function delegateLeadPlan(
  workspaceId: string,
  body: {
    goal: string;
    mode?: LeadPlanMode;
    attachment_ids?: string[];
    source_message_id?: string | null;
    dispatch_workers?: boolean;
  },
): Promise<LeadFanOutResponse> {
  const encoded = encodeURIComponent(workspaceId);
  return fetchJson<LeadFanOutResponse>(
    `/api/workspaces/${encoded}/lead/fan-out`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        goal: body.goal,
        mode: body.mode ?? 'auto',
        create_runs: true,
        attachment_ids: body.attachment_ids ?? [],
        source_message_id: body.source_message_id ?? null,
        dispatch_workers: Boolean(body.dispatch_workers),
        confirmed: true,
      }),
    },
    'lead plan delegation failed',
  );
}
