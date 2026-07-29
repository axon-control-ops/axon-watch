import { computed, onScopeDispose, ref, watch, type Ref } from 'vue';

import {
  fanOutLeadPlan,
  fetchWorkspaceLeadPlans,
  setLeadPlanStatus,
  synthesizeLeadPlan,
  type LeadFanOutInput,
  type LeadPlanRecord,
} from '../../../api/lead-plans-api';
import type { WorkspaceRecord } from '../../../contracts/canonical';
import { COMPANY_REFRESH_MS } from '../../../lib/ui-refresh-guardrails';

interface CreateLeadPlansSliceInput {
  currentWorkspace: Ref<WorkspaceRecord | null>;
}

export function createLeadPlansSlice(input: CreateLeadPlansSliceInput) {
  const leadPlansByWorkspaceId = ref<Record<string, LeadPlanRecord[]>>({});
  const leadPlansError = ref<string | null>(null);
  const leadPlansMutating = ref(false);
  let refreshTimer: ReturnType<typeof setInterval> | null = null;

  function stopRefreshTimer(): void {
    if (refreshTimer !== null) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  }

  function startRefreshTimer(workspaceId: string): void {
    stopRefreshTimer();
    refreshTimer = setInterval(() => {
      void loadLeadPlans(workspaceId);
    }, COMPANY_REFRESH_MS);
  }

  async function loadLeadPlans(workspaceId: string): Promise<void> {
    const cleaned = workspaceId.trim();
    if (!cleaned) {
      return;
    }
    try {
      const snapshot = await fetchWorkspaceLeadPlans(cleaned, { limit: 50 });
      leadPlansByWorkspaceId.value = {
        ...leadPlansByWorkspaceId.value,
        [cleaned]: snapshot.items ?? [],
      };
      leadPlansError.value = null;
    } catch (error) {
      leadPlansError.value =
        error instanceof Error ? error.message : 'Failed to load Lead plans';
    }
  }

  async function fanOutCurrentWorkspaceLeadPlan(
    body: LeadFanOutInput,
  ): Promise<Record<string, unknown> | null> {
    const workspaceId = input.currentWorkspace.value?.workspace_id?.trim() ?? '';
    if (!workspaceId) {
      leadPlansError.value = 'Select a workspace before creating a Lead plan';
      return null;
    }
    leadPlansMutating.value = true;
    try {
      const result = await fanOutLeadPlan(workspaceId, body);
      await loadLeadPlans(workspaceId);
      leadPlansError.value = null;
      return result;
    } catch (error) {
      leadPlansError.value =
        error instanceof Error ? error.message : 'Failed to fan out Lead plan';
      return null;
    } finally {
      leadPlansMutating.value = false;
    }
  }

  async function closeCurrentLeadPlanEngagement(
    planId: string,
    status: 'completed' | 'cancelled' = 'completed',
  ): Promise<boolean> {
    const workspaceId = input.currentWorkspace.value?.workspace_id?.trim() ?? '';
    const cleaned = planId.trim();
    if (!workspaceId || !cleaned) {
      return false;
    }
    leadPlansMutating.value = true;
    try {
      await setLeadPlanStatus(cleaned, status);
      await loadLeadPlans(workspaceId);
      leadPlansError.value = null;
      return true;
    } catch (error) {
      leadPlansError.value =
        error instanceof Error ? error.message : 'Failed to close Lead plan';
      return false;
    } finally {
      leadPlansMutating.value = false;
    }
  }

  async function synthesizeCurrentLeadPlan(planId: string): Promise<boolean> {
    const workspaceId = input.currentWorkspace.value?.workspace_id?.trim() ?? '';
    const cleaned = planId.trim();
    if (!workspaceId || !cleaned) {
      return false;
    }
    leadPlansMutating.value = true;
    try {
      await synthesizeLeadPlan(cleaned);
      await loadLeadPlans(workspaceId);
      leadPlansError.value = null;
      return true;
    } catch (error) {
      leadPlansError.value =
        error instanceof Error ? error.message : 'Failed to synthesize Lead plan';
      return false;
    } finally {
      leadPlansMutating.value = false;
    }
  }

  const leadPlansForCurrentWorkspace = computed(() => {
    const workspaceId = input.currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return [] as LeadPlanRecord[];
    }
    return leadPlansByWorkspaceId.value[workspaceId] ?? [];
  });

  const leadPlanIdByTaskId = computed(() => {
    const map = new Map<string, { planId: string; planKey: string; goal: string }>();
    for (const plan of leadPlansForCurrentWorkspace.value) {
      for (const link of plan.task_links ?? []) {
        if (!link.task_id) {
          continue;
        }
        map.set(link.task_id, {
          planId: plan.plan_id,
          planKey: link.plan_key,
          goal: plan.goal,
        });
      }
    }
    return map;
  });

  watch(
    () => input.currentWorkspace.value?.workspace_id ?? null,
    (workspaceId) => {
      stopRefreshTimer();
      if (workspaceId) {
        void loadLeadPlans(workspaceId);
        startRefreshTimer(workspaceId);
      }
    },
    { immediate: true },
  );

  onScopeDispose(() => {
    stopRefreshTimer();
  });

  return {
    leadPlansByWorkspaceId,
    leadPlansForCurrentWorkspace,
    leadPlanIdByTaskId,
    leadPlansError,
    leadPlansMutating,
    loadLeadPlans,
    fanOutCurrentWorkspaceLeadPlan,
    closeCurrentLeadPlanEngagement,
    synthesizeCurrentLeadPlan,
  };
}
