import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import type { IdeComposerRestoreMode } from '../../lib/ide-composer-restore-request';
import { SERVER_RESTART_CONTINUATION_PROMPT } from '../../lib/ide-run-recovery';
import {
  employeeDockReceiptRunId,
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

export type TeamMemberControlAction = 'toggle_enabled' | 'stop';

export interface TeamMemberQuickAction {
  id: TeamMemberChatKind | TeamMemberSurfaceAction | TeamMemberControlAction;
  label: string;
  kind: 'chat' | 'surface' | 'control';
  chatKind?: TeamMemberChatKind;
  surface?: TeamMemberSurfaceAction;
  control?: TeamMemberControlAction;
  composerMode?: IdeComposerRestoreMode;
}

function ownsSnippet(employee: CompanyEmployeeRecord): string {
  const owns = employee.owns?.trim();
  return owns || employee.role_label?.trim() || employee.role;
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
  const voiceLock =
    'Speak in first person only — never say you are "acting as" a role, ' +
    'Lane B, or VAXON, and never refer to yourself by name in the third person.';
  if (isShiftContinuationFailure(detail)) {
    return (
      `Continue my interrupted shift on ${owns}. ${SERVER_RESTART_CONTINUATION_PROMPT} ` +
      `${voiceLock} Summarize what I changed and include receipts.`
    );
  }
  if (isUsageLimitFailure(employee.last_outcome_detail)) {
    return (
      `Usage limits blocked my last shift on ${owns}. Once limits are restored, ` +
      `I will retry my bounded continuous shift. ${voiceLock} ` +
      `Summarize what I changed and include receipts.`
    );
  }
  if (isRuntimeAuthProbeFailure(employee.last_outcome_detail)) {
    return (
      `Cursor CLI auth probe timed out on my last shift on ${owns}. After checking ` +
      `\`cursor agent status\` on the host, I will retry my bounded continuous shift. ${voiceLock} ` +
      `Summarize what I changed and include receipts.`
    );
  }
  if (isRuntimeAuthFailure(employee.last_outcome_detail)) {
    return (
      `Runtime auth blocked my last shift on ${owns}. After \`cursor agent login\` ` +
      `on the host or /vault unlock, I will retry my bounded continuous shift. ${voiceLock} ` +
      `Summarize what I changed and include receipts.`
    );
  }
  const errorHint = detail ? ` Last error: ${detail}` : '';
  return (
    `My last continuous shift on ${owns} failed.${errorHint} ` +
    `Retry that bounded shift now as me. ${voiceLock} ` +
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
    return (
      `Walk me through what happened on my last job${runHint}. ` +
      `The job never started because usage limits blocked the agent. ` +
      `Summarize what was attempted and suggest next steps once limits are restored.`
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

export function employeeQuickActions(employee: CompanyEmployeeRecord): TeamMemberQuickAction[] {
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
  const actions: TeamMemberQuickAction[] = [
    ...(failed
      ? [
          retryAction,
          ...(employeeDockReceiptRunId(employee) ? [receiptsAction] : []),
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
      label: 'Briefing',
      kind: 'surface',
      surface: 'briefing',
    });
  }

  return actions;
}
