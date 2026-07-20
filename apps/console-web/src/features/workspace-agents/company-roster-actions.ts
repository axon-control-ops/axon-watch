import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import type { IdeComposerRestoreMode } from '../../lib/ide-composer-restore-request';
import { SERVER_RESTART_CONTINUATION_PROMPT } from '../../lib/ide-run-recovery';
import {
  employeeDockReceiptRunId,
  employeeFailureLine,
  isRestartInterruptedFailure,
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
  const name = employee.name.trim() || 'this teammate';
  const owns = ownsSnippet(employee);
  const detail = (employee.last_outcome_detail ?? '').trim();
  if (isRestartInterruptedFailure(detail)) {
    return (
      `${name} (${owns}): ${SERVER_RESTART_CONTINUATION_PROMPT} ` +
      `Summarize what changed and include receipts.`
    );
  }
  const errorHint = detail ? ` Last error: ${detail}` : '';
  return `Retry the last failed shift for ${name} (${owns}).${errorHint} Summarize what changed and include receipts.`;
}

export function employeeReceiptsDraft(employee: CompanyEmployeeRecord): string {
  const name = employee.name.trim() || 'this teammate';
  const runId = employeeDockReceiptRunId(employee);
  const detail = (employee.last_outcome_detail ?? '').trim();
  if (isRestartInterruptedFailure(detail)) {
    const runHint = runId ? ` (${runId})` : '';
    return (
      `Walk me through what was in progress when the server restarted for ${name}'s shift${runHint}. ` +
      `${SERVER_RESTART_CONTINUATION_PROMPT} Summarize what was incomplete, cite commands, and suggest next steps.`
    );
  }
  const detailHint = detail ? ` Error: ${detail}` : '';
  if (runId) {
    return (
      `Walk me through receipts for ${name}'s last shift (${runId}).${detailHint} ` +
      `Summarize what failed, cite commands or assertions, and suggest next steps.`
    );
  }
  return (
    `Walk me through receipts for ${name}'s last failed shift.${detailHint} ` +
    `Summarize what failed and suggest next steps.`
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

export function employeeChatComposerMode(kind: TeamMemberChatKind): IdeComposerRestoreMode {
  if (kind === 'status' || kind === 'receipts') {
    return 'ask';
  }
  return 'agent';
}

export function employeeComposerOpenPayload(
  employee: CompanyEmployeeRecord,
  kind: TeamMemberChatKind,
): { mode: IdeComposerRestoreMode; draft: string } {
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
  const retryAction: TeamMemberQuickAction = {
    id: 'retry',
    label: 'Retry shift',
    kind: 'chat',
    chatKind: 'retry',
    composerMode: 'agent',
  };
  const receiptsAction: TeamMemberQuickAction = {
    id: 'receipts',
    label: 'View receipts',
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
      composerMode: 'ask',
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
      label: 'Stop shift',
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
