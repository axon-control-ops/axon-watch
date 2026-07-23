import type { Ref } from 'vue';

import { createWorkspaceChatThread } from '../../api/control-plane';
import type { WorkspaceChatThreadListItem } from '../../api/control-plane';
import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import { employeeIdeThreadTitle } from '../../features/workspace-agents/employee-thread';
import { sortIdeThreadsNewestFirst } from '../../lib/ide-thread-picker-view';

export interface EnsureCompanyEmployeeIdeTabsInput {
  workspaceId: string;
  companyEmployeesByWorkspaceId: Ref<Record<string, CompanyEmployeeRecord[]>>;
  ideThreadsByWorkspaceId: Ref<Record<string, WorkspaceChatThreadListItem[]>>;
  loadCompanyEmployees: (workspaceId: string) => Promise<void>;
  loadIdeThreads: (workspaceId: string) => Promise<void>;
  getWorkspaceSurfaceThreadId: (workspaceId: string, surface: 'ide') => string | null;
  persistOpenIdeThreadTabs: (workspaceId: string, threadIds: string[]) => void;
  selectIdeThread: (threadId: string) => Promise<void>;
}

export interface HydrateWorkspaceIdeChatInput extends EnsureCompanyEmployeeIdeTabsInput {
  applyIdeThreadMessagesToView: (workspaceId: string) => void;
  bootstrapIdeActiveThreadId: (workspaceId: string) => string | null;
  loadWorkspaceThread: (workspaceId: string, surface: 'ide', threadId: string) => Promise<void>;
}

/** Restore cached IDE chat, hydrate threads, and open teammate tabs when needed. */
export async function hydrateWorkspaceIdeChatImpl(
  input: HydrateWorkspaceIdeChatInput,
): Promise<void> {
  const { workspaceId } = input;
  input.applyIdeThreadMessagesToView(workspaceId);
  await input.loadIdeThreads(workspaceId);
  input.bootstrapIdeActiveThreadId(workspaceId);
  input.applyIdeThreadMessagesToView(workspaceId);
  const threadId = input.getWorkspaceSurfaceThreadId(workspaceId, 'ide');
  if (threadId) {
    await input.loadWorkspaceThread(workspaceId, 'ide', threadId);
    input.applyIdeThreadMessagesToView(workspaceId);
  }
  await ensureCompanyEmployeeIdeTabs(input);
}

/** Open one IDE tab per roster teammate (DashPro-style), focusing Lead when needed. */
export async function ensureCompanyEmployeeIdeTabs(
  input: EnsureCompanyEmployeeIdeTabsInput,
): Promise<void> {
  const { workspaceId } = input;
  await input.loadCompanyEmployees(workspaceId);
  const employees = input.companyEmployeesByWorkspaceId.value[workspaceId] ?? [];
  if (employees.length < 2) {
    return;
  }

  await input.loadIdeThreads(workspaceId);
  let threads = input.ideThreadsByWorkspaceId.value[workspaceId] ?? [];
  const byEmployee = new Map(
    threads
      .filter((thread) => (thread.employee_id ?? '').trim())
      .map((thread) => [(thread.employee_id ?? '').trim(), thread] as const),
  );

  for (const employee of employees) {
    const employeeId = employee.employee_id.trim();
    if (!employeeId || byEmployee.has(employeeId)) {
      continue;
    }
    try {
      const created = await createWorkspaceChatThread(workspaceId, {
        surface: 'ide',
        title: employeeIdeThreadTitle(employee),
        employeeId,
        employeeRole: employee.role,
      });
      byEmployee.set(employeeId, created);
      threads = sortIdeThreadsNewestFirst([
        created,
        ...threads.filter((thread) => thread.thread_id !== created.thread_id),
      ]);
    } catch {
      // Keep hydrating other teammates even if one create fails.
    }
  }

  input.ideThreadsByWorkspaceId.value = {
    ...input.ideThreadsByWorkspaceId.value,
    [workspaceId]: threads,
  };

  const openIds = employees
    .map((employee) => byEmployee.get(employee.employee_id.trim())?.thread_id)
    .filter((threadId): threadId is string => Boolean(threadId));
  if (openIds.length) {
    input.persistOpenIdeThreadTabs(workspaceId, openIds);
  }

  const activeId = input.getWorkspaceSurfaceThreadId(workspaceId, 'ide');
  const activeThread = threads.find((thread) => thread.thread_id === activeId);
  if (activeThread?.employee_id?.trim()) {
    return;
  }
  const primary =
    employees.find((row) => row.primary) ??
    employees.find((row) => row.role === 'lead') ??
    employees[0];
  const primaryThread = primary ? byEmployee.get(primary.employee_id.trim()) : null;
  if (primaryThread?.thread_id) {
    await input.selectIdeThread(primaryThread.thread_id);
  }
}
