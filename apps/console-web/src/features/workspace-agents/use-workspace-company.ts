import { computed, onMounted, onUnmounted, ref, watch, type Ref } from 'vue';

import { fetchWorkspaceCompany } from '../../api/workspace-api';
import type { CompanyEmployeeRecord, CompanyRosterRecord } from '../../contracts/canonical';
import {
  COMPANY_REFRESH_MS,
  companyEmployeesUnchanged,
} from '../../lib/ui-refresh-guardrails';

export { COMPANY_REFRESH_MS } from '../../lib/ui-refresh-guardrails';

export function useWorkspaceCompany(currentWorkspaceId: Ref<string | null | undefined>) {
  const company = ref<CompanyRosterRecord | null>(null);
  const employees = computed<CompanyEmployeeRecord[]>(() => company.value?.employees ?? []);
  const loadState = ref<'idle' | 'loading' | 'loaded' | 'error'>('idle');
  const loadError = ref<string | null>(null);
  let refreshTimer: ReturnType<typeof setInterval> | null = null;

  async function loadCompany(options?: { background?: boolean }): Promise<void> {
    const workspaceId = currentWorkspaceId.value?.trim();
    if (!workspaceId) {
      company.value = null;
      loadState.value = 'idle';
      loadError.value = null;
      return;
    }

    const background = options?.background === true && loadState.value === 'loaded';
    if (!background) {
      loadState.value = 'loading';
      loadError.value = null;
    }
    try {
      const snapshot = await fetchWorkspaceCompany(workspaceId);
      if (
        background &&
        companyEmployeesUnchanged(company.value?.employees, snapshot.company.employees ?? [])
      ) {
        return;
      }
      company.value = snapshot.company;
      loadState.value = 'loaded';
    } catch (error) {
      if (!background) {
        loadState.value = 'error';
        loadError.value = error instanceof Error ? error.message : 'workspace company request failed';
      }
    }
  }

  onMounted(() => {
    void loadCompany();
    refreshTimer = setInterval(() => {
      void loadCompany({ background: true });
    }, COMPANY_REFRESH_MS);
  });

  onUnmounted(() => {
    if (refreshTimer !== null) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  });

  watch(currentWorkspaceId, () => {
    void loadCompany();
  });

  return {
    company,
    employees,
    loadState,
    loadError,
    loadCompany,
  };
}
