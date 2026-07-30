import { fetchPlan } from '../api/plans-api';

import { focusAgentDockComposerInput } from './agent-dock-composer-focus';
import { buildImplementPlanPrompt } from './build-plan-prompt';
import type { IdeComposerMode } from './ide-composer-queue';
import { requestIdeComposerMode } from './ide-composer-restore-request';

export type BuildPlanShell = {
  openIdeComposerWithDraft: (
    content: string,
    options?: { keepActivityView?: boolean },
  ) => void;
  setAgentExecutionAccess: (value: 'consultative' | 'full') => void;
  submitIdeComposer: (
    mode: IdeComposerMode,
    options?: { attachmentFiles?: File[] },
  ) => Promise<boolean | void>;
};

export type BuildPlanResult =
  | { ok: true; prompt: string }
  | { ok: false; reason: string };

export async function buildPlan(
  shell: BuildPlanShell,
  options: {
    workspaceId: string;
    planId: string;
    title?: string;
    /** Skip fetch when the editor already has the plan body. */
    contentOverride?: string;
  },
): Promise<BuildPlanResult> {
  const workspaceId = options.workspaceId.trim();
  const planId = options.planId.trim();
  if (!workspaceId || !planId) {
    return { ok: false, reason: 'Workspace or plan id missing.' };
  }

  let title = options.title?.trim() || '';
  let content = options.contentOverride?.trim() || '';
  if (!content) {
    const plan = await fetchPlan(workspaceId, planId);
    title = title || plan.title.trim();
    content = plan.content.trim();
  }
  if (!content) {
    return { ok: false, reason: 'Plan body was empty.' };
  }

  const prompt = buildImplementPlanPrompt({ planId, title, content });
  // Agent Full + explicit agent submit — bypasses Plan soft-switch UI path.
  requestIdeComposerMode('agent');
  shell.setAgentExecutionAccess('full');
  shell.openIdeComposerWithDraft(prompt);
  focusAgentDockComposerInput();
  await shell.submitIdeComposer('agent');
  return { ok: true, prompt };
}
