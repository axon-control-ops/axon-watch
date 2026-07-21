import { ref, type ComputedRef, type Ref } from 'vue';

import { createWorkspaceHandoff } from '../../../api/control-plane';
import type {
  CompanyEmployeeRecord,
  OperatorBriefing,
  WorkspaceRecord,
} from '../../../contracts/canonical';
import { routeEmployeeSpecialtyTask } from '../../../lib/route-employee-specialty-task';
import {
  readPendingHandoffDismissSignalId,
  writePendingHandoffDismissSignalId,
} from '../../../lib/signal-handoff-dismiss';
import {
  resolveSignalHandoff,
  type SignalHandoffInput,
} from '../../../lib/signal-handoff-view';

type HandoffSliceInput = {
  currentWorkspace: Ref<WorkspaceRecord | null>;
  workspaces: Ref<WorkspaceRecord[]>;
  operatorBriefing: Ref<OperatorBriefing | null>;
  ideComposerDraft: Ref<string>;
  activeIdeThreadId: ComputedRef<string | null>;
  activeIdeEmployeeRecord: ComputedRef<CompanyEmployeeRecord | null>;
  companyEmployeesForCurrentWorkspace: ComputedRef<CompanyEmployeeRecord[]>;
  setCurrentWorkspace: (workspaceId: string) => void;
  setLayoutMode: (mode: 'ide') => void;
  hydrateWorkspaceIdeChat: (workspaceId: string) => Promise<void>;
  loadCompanyEmployees: (workspaceId: string) => Promise<void>;
  openOrFocusEmployeeIdeThread: (employee: {
    employee_id: string;
    name: string;
    role: string;
    role_label?: string;
  }) => Promise<string | null>;
  selectIdeThread: (threadId: string) => Promise<void>;
  createIdeThread: () => Promise<string | null>;
  submitIdeComposer: (mode: 'agent') => Promise<void>;
};

export function createSignalHandoffSlice(input: HandoffSliceInput) {
  const handoffMutationState = ref<'idle' | 'submitting' | 'error'>('idle');
  const handoffMutationError = ref<string | null>(null);
  const lastDiscussedSignal = ref<SignalHandoffInput | null>(null);
  const pendingHandoffDismissSignalId = ref<string | null>(
    readPendingHandoffDismissSignalId(),
  );

  async function openRoutedTask(options: {
    targetWorkspaceId: string;
    task: string;
    employeeId?: string;
    autoSubmit: boolean;
  }): Promise<void> {
    input.setCurrentWorkspace(options.targetWorkspaceId);
    input.setLayoutMode('ide');
    input.ideComposerDraft.value = options.task;
    await input.hydrateWorkspaceIdeChat(options.targetWorkspaceId);
    await input.loadCompanyEmployees(options.targetWorkspaceId);
    await routeEmployeeSpecialtyTask({
      shell: {
        activeIdeThreadId: input.activeIdeThreadId.value,
        activeIdeEmployeeRecord: input.activeIdeEmployeeRecord.value,
        companyEmployeesForCurrentWorkspace:
          input.companyEmployeesForCurrentWorkspace.value,
        openOrFocusEmployeeIdeThread: input.openOrFocusEmployeeIdeThread,
        selectIdeThread: input.selectIdeThread,
        createIdeThread: input.createIdeThread,
      },
      prompt: options.task,
      workspaceId: options.targetWorkspaceId,
      currentEmployee: input.activeIdeEmployeeRecord.value,
      roster: input.companyEmployeesForCurrentWorkspace.value,
      preferredEmployeeId: options.employeeId,
      restorePrompt: (prompt) => {
        input.ideComposerDraft.value = prompt;
      },
      submit: options.autoSubmit ? () => input.submitIdeComposer('agent') : undefined,
    });
  }

  async function handoffSignalToIde(
    signal: SignalHandoffInput,
    options: { autoSubmit?: boolean; employeeId?: string } = {},
  ): Promise<void> {
    handoffMutationState.value = 'submitting';
    handoffMutationError.value = null;
    const spoken = input.operatorBriefing.value?.operator_presence?.spoken_alert;
    const enriched: SignalHandoffInput = {
      ...signal,
      serverExplanation:
        signal.serverExplanation ??
        (spoken?.explanation as Record<string, unknown> | null | undefined) ??
        null,
      serverSignalId: signal.serverSignalId ?? spoken?.signal_id ?? null,
      serverReason: signal.serverReason ?? spoken?.reason ?? null,
    };
    lastDiscussedSignal.value = enriched;
    const resolved = resolveSignalHandoff(
      enriched,
      input.currentWorkspace.value?.workspace_id ?? null,
      input.workspaces.value,
    );
    if (!resolved) {
      handoffMutationState.value = 'error';
      handoffMutationError.value = 'This signal cannot be handed off to the IDE.';
      return;
    }

    try {
      if (resolved.mode === 'handoff' && resolved.sourceWorkspaceId) {
        await createWorkspaceHandoff(resolved.sourceWorkspaceId, {
          target_workspace_id: resolved.targetWorkspaceId,
          task: resolved.task,
          reason: resolved.reason,
        });
      }
      await openRoutedTask({
        targetWorkspaceId: resolved.targetWorkspaceId,
        task: resolved.task,
        employeeId: options.employeeId,
        autoSubmit: Boolean(options.autoSubmit),
      });
      pendingHandoffDismissSignalId.value = resolved.reason;
      writePendingHandoffDismissSignalId(resolved.reason);
      handoffMutationState.value = 'idle';
    } catch (error) {
      handoffMutationState.value = 'error';
      handoffMutationError.value =
        error instanceof Error ? error.message : 'Failed to hand off signal to IDE';
    }
  }

  async function routeTaskToEmployee(options: {
    targetWorkspaceId: string;
    task: string;
    employeeId: string;
  }): Promise<void> {
    handoffMutationState.value = 'submitting';
    handoffMutationError.value = null;
    try {
      await openRoutedTask({ ...options, autoSubmit: true });
      handoffMutationState.value = 'idle';
    } catch (error) {
      handoffMutationState.value = 'error';
      handoffMutationError.value =
        error instanceof Error ? error.message : 'Failed to route task to teammate';
    }
  }

  async function handoffDiscussedSignalToIde(): Promise<void> {
    if (lastDiscussedSignal.value) {
      await handoffSignalToIde(lastDiscussedSignal.value);
    }
  }

  return {
    handoffDiscussedSignalToIde,
    handoffMutationError,
    handoffMutationState,
    handoffSignalToIde,
    lastDiscussedSignal,
    pendingHandoffDismissSignalId,
    routeTaskToEmployee,
  };
}
