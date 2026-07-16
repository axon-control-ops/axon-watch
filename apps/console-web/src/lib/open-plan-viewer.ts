import { fetchPlan } from '../api/plans-api';
import { displayPlanTitle } from './plan-display-title';

export type OpenPlanViewerShell = {
  openAgentContentInEditor: (options: {
    title: string;
    content: string;
    preferPreview?: boolean;
    focus?: boolean;
    readOnly?: boolean;
    planId?: string;
  }) => string | null;
};

export async function openPlanInEditor(input: {
  shell: OpenPlanViewerShell;
  workspaceId: string;
  planId: string;
  fallbackTitle?: string;
}): Promise<string | null> {
  const plan = await fetchPlan(input.workspaceId, input.planId);
  const title = displayPlanTitle(
    plan.title.trim() || input.fallbackTitle?.trim() || '',
    'Plan',
  );
  const body = plan.content.trim();
  if (!body) {
    return null;
  }
  return input.shell.openAgentContentInEditor({
    title: `Plan · ${title}`,
    content: body,
    preferPreview: true,
    focus: true,
    readOnly: true,
    planId: input.planId.trim(),
  });
}
