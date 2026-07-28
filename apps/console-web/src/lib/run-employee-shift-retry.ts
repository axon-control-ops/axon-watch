import type { CompanyEmployeeRecord } from '../contracts/canonical';
import { employeeComposerOpenPayload } from '../features/workspace-agents/company-roster-actions';
import { focusAgentDockComposerInput } from './agent-dock-composer-focus';
import type { IdeComposerMode } from './ide-composer-queue';
import { requestIdeComposerMode } from './ide-composer-restore-request';

export type RunEmployeeShiftRetryShell = {
  setAgentExecutionAccess: (value: 'consultative' | 'full') => void;
  openIdeComposerWithDraft: (
    content: string,
    options?: { keepActivityView?: boolean },
  ) => void;
  openIdeComposer?: (options?: { keepActivityView?: boolean }) => void;
  submitIdeComposer: (
    mode: IdeComposerMode,
    options?: { attachmentFiles?: File[] },
  ) => Promise<void>;
  openOrFocusEmployeeIdeThread?: (employee: {
    employee_id: string;
    name: string;
    role: string;
    role_label?: string;
  }) => Promise<string | null>;
};

export type RunEmployeeShiftRetryResult =
  | { ok: true; draft: string }
  | { ok: false; reason: string };

/**
 * Seed the teammate's agent composer with a retry prompt and submit immediately
 * (same draft+submit pattern as Build plan / signal handoff autoSubmit).
 */
export async function runEmployeeShiftRetry(
  shell: RunEmployeeShiftRetryShell,
  employee: CompanyEmployeeRecord,
  options: { keepActivityView?: boolean; focusThread?: boolean } = {},
): Promise<RunEmployeeShiftRetryResult> {
  const keepActivityView = options.keepActivityView ?? true;
  const focusThread = options.focusThread ?? true;

  if (focusThread && shell.openOrFocusEmployeeIdeThread) {
    await shell.openOrFocusEmployeeIdeThread(employee);
  }

  const { mode, draft } = employeeComposerOpenPayload(employee, 'retry');
  if (!draft.trim()) {
    return { ok: false, reason: 'Retry draft was empty.' };
  }

  if (mode) {
    requestIdeComposerMode(mode);
  }
  shell.setAgentExecutionAccess('full');
  shell.openIdeComposerWithDraft(draft, { keepActivityView });
  focusAgentDockComposerInput();
  await shell.submitIdeComposer('agent');

  return { ok: true, draft };
}
