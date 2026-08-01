/** VAXON Mission Control CEO — ask Leads, rank critical work. */

export type MissionControlCriticalWork = {
  ok: boolean;
  generated_at?: string;
  focused_workspace_id?: string | null;
  leads_asked: number;
  awaiting_plan_count: number;
  leads: Array<{
    workspace_id: string;
    lead_name: string;
    display_name: string;
    owns: string;
    awaiting_engagement_count: number;
    awaiting_engagement_plans: Array<{ plan_id: string; goal: string }>;
  }>;
  winner: {
    kind: string;
    workspace_id?: string | null;
    display_name?: string;
    lead_name?: string;
    plan_id?: string | null;
    title?: string;
  } | null;
  advise: string;
  advise_ui_action?: {
    type: string;
    workspace_id?: string | null;
    focus_attention?: boolean;
    plan_id?: string | null;
  } | null;
};

export async function fetchMissionControlCriticalWork(
  focusedWorkspaceId?: string | null,
): Promise<MissionControlCriticalWork> {
  const query = focusedWorkspaceId?.trim()
    ? `?focused_workspace_id=${encodeURIComponent(focusedWorkspaceId.trim())}`
    : '';
  const response = await fetch(`/api/operator/mission-control/critical-work${query}`, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`critical-work failed: ${response.status}`);
  }
  return (await response.json()) as MissionControlCriticalWork;
}

export type MissionControlEngageLeadsResult = {
  ok: boolean;
  autonomy_full?: boolean;
  engaged: Array<{ plan_id: string; workspace_id: string; goal: string }>;
  remaining: number;
  spoken?: string;
  reason?: string;
};

export async function engageMissionControlLeads(
  maxPlans = 5,
): Promise<MissionControlEngageLeadsResult> {
  const response = await fetch(
    `/api/operator/mission-control/engage-leads?max_plans=${maxPlans}`,
    { method: 'POST', headers: { Accept: 'application/json' } },
  );
  if (!response.ok) {
    throw new Error(`engage-leads failed: ${response.status}`);
  }
  return (await response.json()) as MissionControlEngageLeadsResult;
}
