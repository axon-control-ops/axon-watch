import type { CompanyEmployeeRecord } from '../../contracts/canonical';

export type EmployeeThreadTitleInput = Pick<CompanyEmployeeRecord, 'name' | 'role'> & {
  role_label?: string;
};

export type EmployeeIdeThreadReference = {
  employee_id?: string | null;
  preview_label?: string | null;
};

/** Tab / dock title for a teammate-owned IDE chat thread. */
export function employeeIdeThreadTitle(employee: EmployeeThreadTitleInput): string {
  const name = employee.name.trim() || 'Teammate';
  const role = (employee.role_label || employee.role || 'Agent').trim();
  return `${name} · ${role}`;
}

/**
 * Resolve employee-owned thread chrome from the current workspace roster.
 * Thread titles are persisted snapshots and can retain an old employee name
 * after a workspace roster is renamed.
 */
export function currentEmployeeIdeThreadTitle(
  thread: EmployeeIdeThreadReference,
  employees: readonly (EmployeeThreadTitleInput & { employee_id: string })[],
): string {
  const employeeId = thread.employee_id?.trim();
  const employee = employeeId
    ? employees.find((candidate) => candidate.employee_id === employeeId)
    : null;
  return employee ? employeeIdeThreadTitle(employee) : thread.preview_label?.trim() || 'New chat';
}
