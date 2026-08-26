import type { CompanyEmployeeRecord, RunRecord } from '../../contracts/canonical';
import type { WorkspaceTaskRecord } from '../../api/tasks-api';
import type { IdeComposerRestoreMode } from '../../lib/ide-composer-restore-request';
import { SERVER_RESTART_CONTINUATION_PROMPT } from '../../lib/ide-run-recovery';
import { resolveEmployeeManualHandoff } from './employee-manual-handoff';
import {
  resolveOperatorStartAction,
} from '../../lib/verification-handoff';
import {
  employeeDockReceiptRunId,
  employeeFailureBlocksRetry,
  employeeFailureLine,
  employeeFailureRetryActionLabel,
  isRuntimeAuthFailure,
  isRuntimeAuthProbeFailure,
  isShiftContinuationFailure,
  isUsageLimitFailure,
  looksLikeSuccessfulOutcomeDetail,
  normalizeOperatorFailureDetail,
} from './company-roster-view';

export type TeamMemberChatKind = 'talk' | 'status' | 'assign' | 'retry' | 'receipts';

export type TeamMemberSurfaceAction = 'briefing' | 'attention';

export type TeamMemberControlAction =
  | 'toggle_enabled'
  | 'stop'
  | 'start_now'
  | 'clear_run_card';

export interface TeamMemberQuickAction {
  id: TeamMemberChatKind | TeamMemberSurfaceAction | TeamMemberControlAction;
  label: string;
  kind: 'chat' | 'surface' | 'control';
  chatKind?: TeamMemberChatKind;
  surface?: TeamMemberSurfaceAction;
  control?: TeamMemberControlAction;
  composerMode?: IdeComposerRestoreMode;
  /** Task id for Manual/Semi Start Now handoffs. */
  taskId?: string;
}

function ownsSnippet(employee: CompanyEmployeeRecord): string {
  const owns = employee.owns?.trim();
  return owns || employee.role_label?.trim() || employee.role;
}

function usageRuntime(detail: string | null | undefined): 'Codex' | 'Claude' | 'Cursor' {
  const normalized = (detail ?? '').toLowerCase();
  if (normalized.includes('codex')) return 'Codex';
  if (normalized.includes('claude')) return 'Claude';
  return 'Cursor';
}

/** Talk opens the composer without a starter sentence — speak/status UI already introduces the teammate. */
export function employeeTalkDraft(_employee: CompanyEmployeeRecord): string {
  return '';
}

/** Status is spoken locally from roster state — keep the composer empty so Talk/Status don't fire a CLI ask. */
export function employeeStatusDraft(_employee: CompanyEmployeeRecord): string {
  return '';
}

export function employeeAssignDraft(employee: CompanyEmployeeRecord): string {
  const name = employee.name.trim() || 'this teammate';
  return `Assign to ${name} (${ownsSnippet(employee)}): `;
}

export function employeeRetryDraft(employee: CompanyEmployeeRecord): string {
  const owns = ownsSnippet(employee);
  const detail = normalizeOperatorFailureDetail(employee.last_outcome_detail);
  // No voice/persona steering text here — the backend's employee_persona_prompt.py
  // already injects "speak in first person, never say you're acting as a role"
  // guidance server-side for every employee-persona dispatch. Duplicating it here
  // used to leak an internal instruction into the operator-visible, persisted
  // chat message.
  if (isShiftContinuationFailure(detail)) {
    return (
      `Continue my interrupted shift on ${owns}. ${SERVER_RESTART_CONTINUATION_PROMPT} ` +
      `Summarize what I changed and include receipts.`
    );
  }
  if (isUsageLimitFailure(employee.last_outcome_detail)) {
    const runtime = usageRuntime(employee.last_outcome_detail);
    if (runtime !== 'Cursor') {
      return (
        `The signed-in ${runtime} account quota blocked my last shift on ${owns}. ` +
        `Use an approved Auto fallback runtime, then retry my bounded continuous shift. ` +
        `Summarize what I changed and include receipts.`
      );
    }
    return (
      `A Cursor usage signal blocked my last shift on ${owns}. ` +
      `Auto+Composer or on-demand may still have headroom — check Usage, then ` +
      `I will retry my bounded continuous shift. ` +
      `Summarize what I changed and include receipts.`
    );
  }
  if (isRuntimeAuthProbeFailure(employee.last_outcome_detail)) {
    return (
      `Cursor CLI auth probe timed out on my last shift on ${owns}. After checking ` +
      `\`cursor agent status\` on the host, I will retry my bounded continuous shift. ` +
      `Summarize what I changed and include receipts.`
    );
  }
  if (isRuntimeAuthFailure(employee.last_outcome_detail)) {
    return (
      `Runtime auth blocked my last shift on ${owns}. After \`cursor agent login\` ` +
      `on the host or /vault unlock, I will retry my bounded continuous shift. ` +
      `Summarize what I changed and include receipts.`
    );
  }
  const errorHint = detail ? ` Last error: ${detail}` : '';
  return (
    `My last continuous shift on ${owns} failed.${errorHint} ` +
    `Retry that bounded shift now as me. ` +
    `Summarize what I changed and include receipts.`
  );
}

export function employeeReceiptsDraft(employee: CompanyEmployeeRecord): string {
  const runId = employeeDockReceiptRunId(employee);
  const detail = normalizeOperatorFailureDetail(employee.last_outcome_detail);
  const outcome = (employee.last_outcome ?? '').trim().toLowerCase();
  const runHint = runId ? ` (${runId})` : '';
  const completed =
    outcome === 'completed' ||
    outcome === 'done' ||
    outcome === 'succeeded' ||
    looksLikeSuccessfulOutcomeDetail(detail);

  if (completed) {
    return (
      `Walk me through what I shipped on my last job${runHint}. ` +
      `This run completed successfully — do not treat it as a failure. ` +
      `Summarize what changed, what was verified, any blockers or Lead next items, and suggest the next move.`
    );
  }
  if (isShiftContinuationFailure(detail)) {
    return (
      `Walk me through what was in progress when the server restarted on my job${runHint}. ` +
      `${SERVER_RESTART_CONTINUATION_PROMPT} Summarize what was incomplete, cite commands, and suggest next steps.`
    );
  }
  if (isUsageLimitFailure(employee.last_outcome_detail)) {
    const runtime = usageRuntime(employee.last_outcome_detail);
    if (runtime !== 'Cursor') {
      return (
        `Walk me through what happened on my last job${runHint}. ` +
        `The ${runtime} CLI reported a usage-limit block, but Axon cannot verify the live ` +
        `account quota. Retry once, check approved Auto fallback runtimes, then suggest the next move.`
      );
    }
    return (
      `Walk me through what happened on my last job${runHint}. ` +
      `The job hit a Cursor usage signal — do not claim the whole account is exhausted. ` +
      `Check live Usage pools (Auto+Composer vs API) and whether on-demand is enabled, then suggest the next move.`
    );
  }
  if (isRuntimeAuthProbeFailure(employee.last_outcome_detail)) {
    return (
      `Walk me through what happened on my last job${runHint}. ` +
      `The job could not run because the Cursor CLI auth probe timed out. ` +
      `Summarize what was attempted and suggest next steps after \`cursor agent status\` is healthy.`
    );
  }
  if (isRuntimeAuthFailure(employee.last_outcome_detail)) {
    return (
      `Walk me through what happened on my last job${runHint}. ` +
      `The job could not run because login is not ready. ` +
      `Summarize what was attempted and suggest next steps once auth is fixed.`
    );
  }
  const detailHint = detail ? ` Reported issue: ${detail}.` : '';
  if (runId) {
    return (
      `Walk me through the receipts for my last job (${runId}).${detailHint} ` +
      `Use that run id / control-plane history — do not dig stale autoloop terminal logs. ` +
      `Summarize what went wrong, cite commands or checks, and suggest next steps.`
    );
  }
  return (
    `Walk me through the receipts for my last failed job.${detailHint} ` +
    `Summarize what went wrong and suggest next steps.`
  );
}

export function employeeChatDraft(
  employee: CompanyEmployeeRecord,
  kind: TeamMemberChatKind,
): string {
  if (kind === 'status') {
    return employeeStatusDraft(employee);
  }
  if (kind === 'assign') {
    return employeeAssignDraft(employee);
  }
  if (kind === 'retry') {
    return employeeRetryDraft(employee);
  }
  if (kind === 'receipts') {
    return employeeReceiptsDraft(employee);
  }
  return employeeTalkDraft(employee);
}

/**
 * Composer mode to open for a roster chat action.
 * `null` = keep the current mode (Status is voice + focus only).
 */
export function employeeChatComposerMode(
  kind: TeamMemberChatKind,
): IdeComposerRestoreMode | null {
  if (kind === 'status') {
    return null;
  }
  if (kind === 'receipts') {
    return 'ask';
  }
  return 'agent';
}

export function employeeComposerOpenPayload(
  employee: CompanyEmployeeRecord,
  kind: TeamMemberChatKind,
): { mode: IdeComposerRestoreMode | null; draft: string } {
  return {
    mode: employeeChatComposerMode(kind),
    draft: employeeChatDraft(employee, kind).trim(),
  };
}

export function employeeSurfaceAction(
  employee: CompanyEmployeeRecord,
): TeamMemberSurfaceAction | null {
  const role = (employee.role ?? '').trim().toLowerCase();
  if (role === 'watcher') {
    return 'attention';
  }
  if (role === 'lead' || employee.primary) {
    return 'briefing';
  }
  return null;
}

/** Hide duplicate "View receipts" when the dock receipt run link already opens receipts. */
export function employeeDockDisplayActions(
  actions: readonly TeamMemberQuickAction[],
  employee: CompanyEmployeeRecord,
): TeamMemberQuickAction[] {
  if (!employeeDockReceiptRunId(employee)) {
    return [...actions];
  }
  return actions.filter((action) => action.id !== 'receipts');
}

export function employeeQuickActions(
  employee: CompanyEmployeeRecord,
  options?: {
    autonomyMode?: string | null;
    tasks?: readonly WorkspaceTaskRecord[];
    runs?: readonly Pick<RunRecord, 'run_id' | 'task_id'>[];
    liveBusy?: boolean;
  },
): TeamMemberQuickAction[] {
  const failed = Boolean(employeeFailureLine(employee));
  const talkAction: TeamMemberQuickAction = {
    id: 'talk',
    label: 'Talk',
    kind: 'chat',
    chatKind: 'talk',
    composerMode: 'agent',
  };
  // Always keep a real retry control on failed jobs. Usage-limit cases still warn in
  // the failure line copy — do not swap retry for receipts (that id is stripped when
  // the dock already links the failed run).
  const retryAction: TeamMemberQuickAction = {
    id: 'retry',
    label: employeeFailureRetryActionLabel(employee),
    kind: 'chat',
    chatKind: 'retry',
    composerMode: 'agent',
  };
  const receiptsAction: TeamMemberQuickAction = {
    id: 'receipts',
    label: 'Explain what happened',
    kind: 'chat',
    chatKind: 'receipts',
    composerMode: 'ask',
  };
  const clearRunAction: TeamMemberQuickAction = {
    id: 'clear_run_card',
    label: 'Clear run',
    kind: 'control',
    control: 'clear_run_card',
  };
  // Working-as-intended policy blocks (e.g. private-document paths) fail the
  // same way on every retry — offering "Try again" here just burns a shift.
  const blocksRetry = failed && employeeFailureBlocksRetry(employee);
  const actions: TeamMemberQuickAction[] = [
    ...(failed
      ? [
          ...(blocksRetry ? [] : [retryAction]),
          ...(employeeDockReceiptRunId(employee) ? [receiptsAction] : []),
          clearRunAction,
          talkAction,
        ]
      : [talkAction]),
    {
      id: 'status',
      label: 'Status',
      kind: 'chat',
      chatKind: 'status',
      // No composerMode — Status speaks locally and must not demote Full Access to Ask.
    },
    {
      id: 'assign',
      label: 'Assign',
      kind: 'chat',
      chatKind: 'assign',
      composerMode: 'agent',
    },
    {
      id: 'toggle_enabled',
      label: employee.enabled ? 'Pause agent' : 'Enable agent',
      kind: 'control',
      control: 'toggle_enabled',
    },
  ];

  const handoff = resolveEmployeeManualHandoff({
    employee,
    autonomyMode: options?.autonomyMode,
    tasks: options?.tasks ?? [],
    runs: options?.runs,
    liveBusy: options?.liveBusy,
  });
  const operatorStart = resolveOperatorStartAction({
    employee,
    tasks: options?.tasks ?? [],
    runs: options?.runs,
    handoffTaskId: handoff.waiting ? handoff.taskId : null,
    liveBusy: options?.liveBusy,
  });
  if (operatorStart) {
    actions.unshift({
      id: 'start_now',
      label: operatorStart.label,
      kind: 'control',
      control: 'start_now',
      taskId: operatorStart.taskId,
    });
  }

  if (employee.active_run_id) {
    actions.push({
      id: 'stop',
      label: 'Stop',
      kind: 'control',
      control: 'stop',
    });
  }

  const surface = employeeSurfaceAction(employee);
  if (surface === 'attention') {
    actions.push({
      id: 'attention',
      label: 'Signals',
      kind: 'surface',
      surface: 'attention',
    });
  } else if (surface === 'briefing') {
    actions.push({
      id: 'briefing',
      label: 'Lead report',
      kind: 'surface',
      surface: 'briefing',
    });
  }

  return actions;
}
