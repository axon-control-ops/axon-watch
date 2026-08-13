import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import type { AgentQuestionOption } from '../../lib/agent-question-view';

const FAILED_SHIFT_TITLE_RE = /^(.+?)\s+\(([^)]+)\)\s+last shift failed/i;

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
  const options = (employee.pending_decision_options ?? [])
    .map((option) => option.label?.trim())
    .filter(Boolean);
  if (!prompt && !options.length) {
    return '';
  }
  if (!options.length) {
    return `${prompt}\n\n`;
  }
  return `${prompt}\n\nOptions: ${options.join(' · ')}\n\nMy decision: `;
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
    const subject = failedShiftSubjectFromDecisionTitle(row.pending_decision_title);
    const holderRole = (row.role ?? '').trim().toLowerCase();
    if (subject && subject.role !== holderRole) {
      return `${holder} needs your decision about ${subject.name} (${subject.role}) — tap to open their dock.`;
    }
    return `${holder} needs your decision — tap to open their dock and choose an option.`;
  }
  return `${pending.length} teammates need your decision — tap to open the first one.`;
}
