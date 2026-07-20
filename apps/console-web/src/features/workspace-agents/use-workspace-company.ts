import { computed, onMounted, onUnmounted, ref, watch, type Ref } from 'vue';

import { fetchWorkspaceCompany } from '../../api/workspace-api';
import type { CompanyEmployeeRecord, CompanyRosterRecord } from '../../contracts/canonical';

/** Shared poll interval for workspace company roster snapshots. */
export const COMPANY_REFRESH_MS = 12_000;

export function useWorkspaceCompany(currentWorkspaceId: Ref<string | null | undefined>) {
  const company = ref<CompanyRosterRecord | null>(null);
  const employees = computed<CompanyEmployeeRecord[]>(() => company.value?.employees ?? []);
  const loadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('idle');
  const loadError = ref<string | null>(null);
  let refreshTimer: ReturnType<typeof setInterval> | null = null;

  async function loadCompany(options?: { reason?: string }): Promise<void> {
    const workspaceId = currentWorkspaceId.value?.trim();
    if (!workspaceId) {
      company.value = null;
      loadState.value = 'idle';
      loadError.value = null;
      return;
    }

    loadState.value = 'loading';
    loadError.value = null;
    try {
      const snapshot = await fetchWorkspaceCompany(workspaceId);
      company.value = snapshot.company;
      loadState.value = 'loaded';
    } catch (error) {
      loadState.value = 'error';
      loadError.value = error instanceof Error ? error.message : 'workspace company request failed';
    }
  }

  onMounted(() => {
    void loadCompany({ reason: 'mount' });
    refreshTimer = setInterval(() => {
      void loadCompany({ reason: 'interval' });
    }, COMPANY_REFRESH_MS);
  });

  onUnmounted(() => {
    if (refreshTimer !== null) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  });

  watch(currentWorkspaceId, () => {
    void loadCompany({ reason: 'workspace-change' });
  });

  return {
    company,
    employees,
    loadState,
    loadError,
    loadCompany,
  };
}
