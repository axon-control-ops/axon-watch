import { computed, ref, type ComputedRef, type Ref } from 'vue';

import { buildPlan } from '../lib/build-plan-action';
import type { WorkspaceDocumentDescriptor } from '../lib/workspace-documents';

type EditorPlanBuildShell = {
  currentWorkspace: { workspace_id: string } | null;
  activeEditorDocument: WorkspaceDocumentDescriptor | null;
  openIdeComposerWithDraft: (content: string) => void;
  setAgentExecutionAccess: (value: 'consultative' | 'full') => void;
  submitIdeComposer: (
    mode: 'ask' | 'plan' | 'agent' | 'debug',
    options?: { attachmentFiles?: File[] },
  ) => Promise<boolean | 'queued' | void>;
};

export function useEditorPlanBuild(shell: EditorPlanBuildShell): {
  activePlanId: ComputedRef<string>;
  buildingPlan: Ref<boolean>;
  buildPlanError: Ref<string>;
  buildActivePlan: () => Promise<void>;
} {
  const activePlanId = computed(() => shell.activeEditorDocument?.planId?.trim() || '');
  const buildingPlan = ref(false);
  const buildPlanError = ref('');

  async function buildActivePlan(): Promise<void> {
    const workspaceId = shell.currentWorkspace?.workspace_id?.trim();
    const planId = activePlanId.value;
    if (!workspaceId || !planId || buildingPlan.value) {
      return;
    }
    buildingPlan.value = true;
    buildPlanError.value = '';
    try {
      const result = await buildPlan(shell, {
        workspaceId,
        planId,
        title: shell.activeEditorDocument?.title,
        contentOverride: shell.activeEditorDocument?.value,
      });
      if (!result.ok) {
        buildPlanError.value = result.reason;
      }
    } catch (err) {
      buildPlanError.value = err instanceof Error ? err.message : 'Unable to build plan.';
    } finally {
      buildingPlan.value = false;
    }
  }

  return {
    activePlanId,
    buildingPlan,
    buildPlanError,
    buildActivePlan,
  };
}
