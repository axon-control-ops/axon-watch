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
 *
 * Usage-limit failures still get a real submit — the failure line already warns the
 * operator; silently no-op'ing Try again made the Team button look broken.
 */
export async function runEmployeeShiftRetry(
  shell: RunEmployeeShiftRetryShell,
  employee: CompanyEmployeeRecord,
  options: { keepActivityView?: boolean; focusThread?: boolean } = {},
): Promise<RunEmployeeShiftRetryResult> {
  const keepActivityView = options.keepActivityView ?? true;
  const focusThread = options.focusThread ?? true;

  // #region agent log
  fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'retry-click',hypothesisId:'H1',location:'run-employee-shift-retry.ts:start',message:'retry shift invoked',data:{employeeId:employee.employee_id,name:employee.name,lastOutcome:employee.last_outcome??null,detailPreview:String(employee.last_outcome_detail||'').slice(0,160),focusThread,keepActivityView},timestamp:Date.now()})}).catch(()=>{});
  // #endregion

  if (focusThread && shell.openOrFocusEmployeeIdeThread) {
    await shell.openOrFocusEmployeeIdeThread(employee);
  }

  const { mode, draft } = employeeComposerOpenPayload(employee, 'retry');
  if (!draft.trim()) {
    // #region agent log
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'retry-click',hypothesisId:'H2',location:'run-employee-shift-retry.ts:empty',message:'retry aborted empty draft',data:{employeeId:employee.employee_id},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    return { ok: false, reason: 'Retry draft was empty.' };
  }

  if (mode) {
    requestIdeComposerMode(mode);
  }
  shell.setAgentExecutionAccess('full');
  shell.openIdeComposerWithDraft(draft, { keepActivityView });
  focusAgentDockComposerInput();
  await shell.submitIdeComposer('agent');

  // #region agent log
  fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'retry-click',hypothesisId:'H1',location:'run-employee-shift-retry.ts:submitted',message:'retry draft submitted',data:{employeeId:employee.employee_id,mode:mode??null,draftChars:draft.length,draftPreview:draft.slice(0,140)},timestamp:Date.now()})}).catch(()=>{});
  // #endregion

  return { ok: true, draft };
}
