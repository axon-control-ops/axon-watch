import { computed, onScopeDispose, ref, watch, type ComputedRef, type Ref } from 'vue';

import { fetchWorkspaceCompany } from '../../../api/workspace-api';
import type { WorkspaceChatThreadListItem } from '../../../api/chat-api';
import type { CompanyEmployeeRecord, WorkspaceRecord } from '../../../contracts/canonical';
import {
  resolveActiveIdeEmployee,
  resolveActiveIdeEmployeeRecord,
  resolveIdeThreadEmployeeFailure,
  type ActiveIdeEmployeeView,
} from '../../../features/workspace-agents/active-ide-employee';
import { employeeShiftNeedsContinuation } from '../../../features/workspace-agents/company-roster-view';
import { COMPANY_REFRESH_MS } from '../../../features/workspace-agents/use-workspace-company';
import { companyEmployeesUnchanged } from '../../../lib/ui-refresh-guardrails';

interface CreateCompanyRosterSliceInput {
  currentWorkspace: Ref<WorkspaceRecord | null>;
  activeIdeThreadId: ComputedRef<string | null>;
  ideThreadsForCurrentWorkspace: ComputedRef<WorkspaceChatThreadListItem[]>;
  /** When a shift stream ends, refresh roster so failure hints stay in sync with the team panel. */
  agentStreamActive?: Ref<boolean>;
}

export function createCompanyRosterSlice(input: CreateCompanyRosterSliceInput) {
  const companyEmployeesByWorkspaceId = ref<Record<string, CompanyEmployeeRecord[]>>({});
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
      void loadCompanyEmployees(workspaceId);
    }, COMPANY_REFRESH_MS);
  }

  async function loadCompanyEmployees(workspaceId: string): Promise<void> {
    const cleaned = workspaceId.trim();
    if (!cleaned) {
      return;
    }
    try {
      const snapshot = await fetchWorkspaceCompany(cleaned);
      const nextEmployees = snapshot.company.employees ?? [];
      const previous = companyEmployeesByWorkspaceId.value[cleaned];
      // #region agent log
      fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'fc0b35'},body:JSON.stringify({sessionId:'fc0b35',runId:'roster-poll',hypothesisId:'H4',location:'create-company-roster-slice.ts:loadCompanyEmployees',message:'company roster poll received',data:{workspaceId:cleaned,unchanged:companyEmployeesUnchanged(previous,nextEmployees),employees:nextEmployees.map((row)=>({role:row.role,status:row.status ?? null,outcome:row.last_outcome ?? null,activeRun:Boolean((row.active_run_id ?? '').trim()),lastRunId:row.last_run_id ?? null}))},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
      if (companyEmployeesUnchanged(previous, nextEmployees)) {
        return;
      }
      companyEmployeesByWorkspaceId.value = {
        ...companyEmployeesByWorkspaceId.value,
        [cleaned]: nextEmployees,
      };
    } catch {
      // Dock identity can still fall back to thread title metadata.
    }
  }

  const activeIdeThread = computed(() => {
    const threadId = input.activeIdeThreadId.value;
    if (!threadId) {
      return null;
    }
    return (
      input.ideThreadsForCurrentWorkspace.value.find((thread) => thread.thread_id === threadId) ??
      null
    );
  });

  const companyEmployeesForCurrentWorkspace = computed(() => {
    const workspaceId = input.currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return [] as CompanyEmployeeRecord[];
    }
    return companyEmployeesByWorkspaceId.value[workspaceId] ?? [];
  });

  const activeIdeEmployee = computed<ActiveIdeEmployeeView | null>(() =>
    resolveActiveIdeEmployee({
      thread: activeIdeThread.value,
      employees: companyEmployeesForCurrentWorkspace.value,
    }),
  );

  const activeIdeEmployeeRecord = computed(() =>
    resolveActiveIdeEmployeeRecord({
      thread: activeIdeThread.value,
      employees: companyEmployeesForCurrentWorkspace.value,
    }),
  );

  const activeIdeEmployeeFailureLine = computed(() =>
    resolveIdeThreadEmployeeFailure({
      thread: activeIdeThread.value,
      employees: companyEmployeesForCurrentWorkspace.value,
    }),
  );

  const activeIdeEmployeeShiftInterrupted = computed(() => {
    const row = activeIdeEmployeeRecord.value;
    return row ? employeeShiftNeedsContinuation(row) : false;
  });

  watch(
    () => input.currentWorkspace.value?.workspace_id ?? null,
    (workspaceId) => {
      stopRefreshTimer();
      if (workspaceId) {
        void loadCompanyEmployees(workspaceId);
        startRefreshTimer(workspaceId);
      }
    },
    { immediate: true },
  );

  if (input.agentStreamActive) {
    watch(input.agentStreamActive, (active, wasActive) => {
      const workspaceId = input.currentWorkspace.value?.workspace_id;
      if (!active && wasActive && workspaceId) {
        void loadCompanyEmployees(workspaceId);
      }
    });
  }

  onScopeDispose(() => {
    stopRefreshTimer();
  });

  return {
    companyEmployeesByWorkspaceId,
    companyEmployeesForCurrentWorkspace,
    activeIdeThread,
    activeIdeEmployee,
    activeIdeEmployeeRecord,
    activeIdeEmployeeFailureLine,
    activeIdeEmployeeShiftInterrupted,
    loadCompanyEmployees,
  };
}
