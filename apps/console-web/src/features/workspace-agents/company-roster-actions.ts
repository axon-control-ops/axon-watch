import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import type { IdeComposerRestoreMode } from '../../lib/ide-composer-restore-request';

export type TeamMemberChatKind = 'talk' | 'status' | 'assign';

export type TeamMemberSurfaceAction = 'briefing' | 'attention';

export interface TeamMemberQuickAction {
  id: TeamMemberChatKind | TeamMemberSurfaceAction;
  label: string;
  kind: 'chat' | 'surface';
  chatKind?: TeamMemberChatKind;
  surface?: TeamMemberSurfaceAction;
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

export function employeeStatusDraft(employee: CompanyEmployeeRecord): string {
  const name = employee.name.trim() || 'this teammate';
  return `Ask ${name} for a short status on ${ownsSnippet(employee)}. Highlight blockers and what needs a decision.`;
}

export function employeeAssignDraft(employee: CompanyEmployeeRecord): string {
  const name = employee.name.trim() || 'this teammate';
  return `Assign to ${name} (${ownsSnippet(employee)}): `;
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
  return employeeTalkDraft(employee);
}

export function employeeChatComposerMode(kind: TeamMemberChatKind): IdeComposerRestoreMode {
  if (kind === 'status') {
    return 'ask';
  }
  return 'agent';
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

export function employeeQuickActions(employee: CompanyEmployeeRecord): TeamMemberQuickAction[] {
  const actions: TeamMemberQuickAction[] = [
    {
      id: 'talk',
      label: 'Talk',
      kind: 'chat',
      chatKind: 'talk',
      composerMode: 'agent',
    },
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
  ];

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
