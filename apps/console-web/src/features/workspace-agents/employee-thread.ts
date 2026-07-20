import type { CompanyEmployeeRecord } from '../../contracts/canonical';

export type EmployeeThreadTitleInput = Pick<CompanyEmployeeRecord, 'name' | 'role'> & {
  role_label?: string;
};

/** Tab / dock title for a teammate-owned IDE chat thread. */
export function employeeIdeThreadTitle(employee: EmployeeThreadTitleInput): string {
  const name = employee.name.trim() || 'Teammate';
  const role = (employee.role_label || employee.role || 'Agent').trim();
  return `${name} · ${role}`;
}
