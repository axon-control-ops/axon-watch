/** Guardrails that keep IDE chrome from remounting/flickering on background polls. */

import type { CompanyEmployeeRecord } from '../contracts/canonical';

/** Shared roster poll interval — keep modest; UI must not remount when payloads are unchanged. */
export const COMPANY_REFRESH_MS = 20_000;

/** Stable fingerprint so identical roster polls do not replace reactive refs. */
export function companyEmployeesFingerprint(
  employees: readonly CompanyEmployeeRecord[] | null | undefined,
): string {
  if (!employees?.length) {
    return '';
  }
  return employees
    .map((row) =>
      [
        row.employee_id,
        row.status ?? '',
        row.last_outcome ?? '',
        row.last_outcome_detail ?? '',
        row.last_run_id ?? '',
        row.active_run_id ?? '',
        row.enabled === false ? '0' : '1',
      ].join('\x1f'),
    )
    .join('\x1e');
}

export function companyEmployeesUnchanged(
  previous: readonly CompanyEmployeeRecord[] | null | undefined,
  next: readonly CompanyEmployeeRecord[] | null | undefined,
): boolean {
  return companyEmployeesFingerprint(previous) === companyEmployeesFingerprint(next);
}
