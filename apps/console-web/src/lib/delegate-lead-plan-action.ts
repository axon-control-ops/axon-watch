import { delegateLeadPlan, previewLeadPlan, type LeadTaskPlan } from '../api/lead-planner-api';
import { fetchPlan } from '../api/plans-api';

export type DelegateLeadPlanResult =
  | {
      ok: true;
      preview: LeadTaskPlan;
      planId: string;
      runCount: number;
      taskCount: number;
    }
  | { ok: false; reason: string; preview?: LeadTaskPlan };

function extractOperatorGoal(planContent: string, title: string): string {
  const body = String(planContent || '').trim();
  if (!body) {
    return title.trim() || 'Execute the saved Lead plan';
  }
  const goalMatch = body.match(/##\s*Goal\s*\n+([\s\S]*?)(?:\n##|\n#|$)/i);
  if (goalMatch?.[1]?.trim()) {
    return goalMatch[1].trim().replace(/\s+/g, ' ');
  }
  // Prefer the original operator prompt when the plan embeds it.
  const firstParagraph = body
    .split(/\n{2,}/)
    .map((part) => part.replace(/^#+\s*/, '').trim())
    .find((part) => part.length > 40);
  return firstParagraph || title.trim() || body.slice(0, 400);
}

export async function previewLeadDelegation(options: {
  workspaceId: string;
  planId: string;
  title?: string;
  contentOverride?: string;
  attachmentIds?: string[];
  sourceMessageId?: string | null;
}): Promise<DelegateLeadPlanResult> {
  const workspaceId = options.workspaceId.trim();
  const planId = options.planId.trim();
  if (!workspaceId || !planId) {
    return { ok: false, reason: 'Workspace or plan id missing.' };
  }

  let title = options.title?.trim() || '';
  let content = options.contentOverride?.trim() || '';
  let sourceMessageId = options.sourceMessageId?.trim() || '';
  if (!content) {
    const plan = await fetchPlan(workspaceId, planId);
    title = title || plan.title.trim();
    content = plan.content.trim();
    sourceMessageId = sourceMessageId || plan.source_message_id.trim();
  }
  if (!content) {
    return { ok: false, reason: 'Plan body was empty.' };
  }

  const goal = extractOperatorGoal(content, title);
  const preview = await previewLeadPlan(workspaceId, {
    goal,
    attachment_ids: options.attachmentIds ?? [],
    source_message_id: sourceMessageId || null,
  });
  return {
    ok: true,
    preview: preview.plan,
    planId: '',
    runCount: 0,
    taskCount: preview.plan.items.length,
  };
}

export async function confirmLeadDelegation(options: {
  workspaceId: string;
  planId: string;
  title?: string;
  contentOverride?: string;
  attachmentIds?: string[];
  sourceMessageId?: string | null;
  dispatchWorkers?: boolean;
}): Promise<DelegateLeadPlanResult> {
  const preview = await previewLeadDelegation(options);
  if (!preview.ok) {
    return preview;
  }

  const workspaceId = options.workspaceId.trim();
  const result = await delegateLeadPlan(workspaceId, {
    goal: preview.preview.goal,
    attachment_ids: options.attachmentIds ?? [],
    source_message_id: options.sourceMessageId ?? null,
    dispatch_workers: options.dispatchWorkers ?? false,
  });

  return {
    ok: true,
    preview: result.plan,
    planId: result.plan_id,
    runCount: result.runs?.length ?? 0,
    taskCount: result.tasks?.length ?? 0,
  };
}
