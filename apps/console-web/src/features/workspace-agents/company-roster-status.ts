const WORKING_STATUSES = new Set([
  'watching',
  'planning',
  'executing',
  'verifying',
  'blocked',
  'waiting_approval',
  'handoff_ready',
]);

export function employeeIsWorking(status: string | null | undefined): boolean {
  return WORKING_STATUSES.has((status ?? '').trim());
}
