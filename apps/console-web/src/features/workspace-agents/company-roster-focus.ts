import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import type { AgentQuestionOption } from '../../lib/agent-question-view';

const FAILED_SHIFT_TITLE_RE = /^(.+?)\s+\(([^)]+)\)\s+last shift failed/i;

export const APPROVE_PENDING_RECOVERY_ID = '__approve_bounded_recovery__';
export const DISMISS_PENDING_DECISION_ID = '__dismiss_pending_decision__';

/** Supply executable controls for generic gated receipts that have no choices. */
export function pendingDecisionCardOptions(
  employee: CompanyEmployeeRecord,
): AgentQuestionOption[] {
  const supplied = (employee.pending_decision_options ?? []).filter(
    (option) => Boolean(option.id?.trim() || option.label?.trim()),
  );
  if (supplied.length || !employee.pending_decision_id?.trim()) {
    return supplied;
  }
  const subject = failedShiftSubject(employee);
  const holder = employee.name.trim() || employee.role_label?.trim() || 'Watcher';
  const sameOwner = subject?.role === (employee.role ?? '').trim().toLowerCase();
  return [
    {
      id: APPROVE_PENDING_RECOVERY_ID,
      label: sameOwner && subject ? `Retry ${subject.name} now` : `Assign ${holder} to diagnose`,
    },
    { id: DISMISS_PENDING_DECISION_ID, label: 'Dismiss — already recovered' },
  ];
}

export function pendingDecisionDirectResolution(
  optionId: string | null | undefined,
): 'approved' | 'rejected' | null {
  if (optionId === APPROVE_PENDING_RECOVERY_ID) {
    return 'approved';
  }
  if (optionId === DISMISS_PENDING_DECISION_ID) {
    return 'rejected';
  }
  return null;
}

/** Parse "Dana (lead) last shift failed" style autonomy titles. */
export function failedShiftSubjectFromDecisionTitle(
  title: string | null | undefined,
): { name: string; role: string } | null {
  const normalized = (title ?? '').trim();
  if (!normalized) {
    return null;
  }
  const match = FAILED_SHIFT_TITLE_RE.exec(normalized);
  if (!match) {
    return null;
  }
  const name = match[1]?.trim();
  const role = match[2]?.trim().toLowerCase();
  if (!name || !role) {
    return null;
  }
  return { name, role };
}

/** Prefer structured receipt identity; retain title parsing for older receipts. */
export function failedShiftSubject(
  employee: CompanyEmployeeRecord,
): { name: string; role: string } | null {
  const fromTitle = failedShiftSubjectFromDecisionTitle(employee.pending_decision_title);
  const structuredRole = employee.pending_decision_subject_role?.trim().toLowerCase();
  if (!structuredRole) {
    return fromTitle;
  }
  return {
    name: fromTitle?.role === structuredRole ? fromTitle.name : structuredRole,
    role: structuredRole,
  };
}

export function findRosterEmployeeByRole(
  employees: readonly CompanyEmployeeRecord[],
  role: string | null | undefined,
): CompanyEmployeeRecord | null {
  const normalized = (role ?? '').trim().toLowerCase();
  if (!normalized) {
    return null;
  }
  return employees.find((row) => (row.role ?? '').trim().toLowerCase() === normalized) ?? null;
}

/** Resolve the prompt shown in autonomy / worker-ask decision cards. */
export function pendingDecisionPrompt(employee: CompanyEmployeeRecord): string {
  return (
    employee.pending_decision_prompt?.trim()
    || employee.pending_decision_title?.replace(/^.+? needs a decision:\s*/i, '').trim()
    || employee.pending_decision_title?.trim()
    || ''
  );
}

/** Seed the agent composer when the operator opens a pending VAXON decision. */
export function buildPendingDecisionComposerDraft(
  employee: CompanyEmployeeRecord,
): string {
  const prompt = pendingDecisionPrompt(employee);
  const subject = failedShiftSubject(employee);
  const reason = String(employee.pending_decision_reason || '').trim();
  const holder = employee.name.trim() || employee.role_label?.trim() || 'Teammate';
  const options = pendingDecisionCardOptions(employee)
    .map((option) => option.label?.trim())
    .filter(Boolean);

  const lines: string[] = [];
  if (subject) {
    lines.push(`Decision required — ${subject.name} (${subject.role}) last shift failed`);
    if (subject.role !== (employee.role ?? '').trim().toLowerCase()) {
      lines.push(`${holder} is holding this decision for ${subject.name} (${subject.role}).`);
    }
  } else if (prompt) {
    lines.push(`Decision required — ${prompt}`);
  } else {
    lines.push('Decision required — review the failed shift and choose next steps.');
  }

  if (prompt && !lines.some((line) => line.includes(prompt))) {
    lines.push(prompt);
  }
  if (reason && reason !== prompt && !lines.includes(reason)) {
    lines.push(`Context: ${reason}`);
  }

  if (options.length) {
    lines.push('', `Options: ${options.join(' · ')}`, '', 'My decision: ');
    return `${lines.join('\n')}`;
  }

  lines.push('', 'My decision: ');
  return lines.join('\n');
}

export function buildPendingDecisionOptionAnswer(
  employee: CompanyEmployeeRecord,
  option: AgentQuestionOption,
): string {
  const prompt = pendingDecisionPrompt(employee);
  const id = option.id.trim();
  const label = option.label.trim();
  if (!id && !label) {
    return '';
  }
  const choice =
    label && id && id !== label ? `Selected option ${id}: ${label}` : `Selected option ${label || id}`;
  if (!prompt) {
    return `${choice}\n\n`;
  }
  return `${choice}\n(answer to: ${prompt})\n\n`;
}

/** Header hint when any teammate is waiting on a VAXON decision. */
export function companyPendingDecisionHint(
  employees: readonly CompanyEmployeeRecord[] | null | undefined,
): string | null {
  const pending = (employees ?? []).filter((row) => Boolean(row.pending_decision_id?.trim()));
  if (!pending.length) {
    return null;
  }
  if (pending.length === 1) {
    const row = pending[0];
    const holder = row.name.trim() || 'A teammate';
    const subject = failedShiftSubject(row);
    const holderRole = (row.role ?? '').trim().toLowerCase();
    if (subject && subject.role !== holderRole) {
      return `${holder} needs your decision about ${subject.name} (${subject.role}) — tap to open their dock.`;
    }
    return `${holder} needs your decision — tap to open their dock and choose an option.`;
  }
  return `${pending.length} teammates need your decision — tap to open the first one.`;
}
