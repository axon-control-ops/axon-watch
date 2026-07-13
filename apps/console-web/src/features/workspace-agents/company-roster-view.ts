import type { CompanyEmployeeRecord } from '../../contracts/canonical';

export function employeeStatusLabel(status: string | null | undefined): string {
  const value = (status ?? '').trim();
  if (!value) {
    return 'idle';
  }
  return value.replace(/_/g, ' ');
}

export function employeeMetaLine(employee: CompanyEmployeeRecord): string {
  const role = employee.role_label?.trim() || employee.role;
  const schedule = employee.schedule_label?.trim() || employee.schedule;
  return `${role} · ${schedule}`;
}

export function companyHeadline(
  companyName: string | null | undefined,
  employeeCount: number | null | undefined,
): string {
  const name = (companyName ?? '').trim() || 'Company';
  const count = typeof employeeCount === 'number' ? employeeCount : 0;
  if (count <= 0) {
    return name;
  }
  return `${name} · ${count} employee${count === 1 ? '' : 's'}`;
}
