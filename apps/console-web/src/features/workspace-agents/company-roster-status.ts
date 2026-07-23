const WORKING_STATUSES = new Set([
  'watching',
  'assigned',
  'planning',
  'executing',
  'verifying',
  'blocked',
  'waiting_approval',
  'handoff_ready',
]);

/** Mid-shift / in-flight work — excludes always-on "watching" and assigned-not-dispatched. */
const ACTIVE_BUSY_STATUSES = new Set([
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

export function employeeStatusIsActivelyBusy(status: string | null | undefined): boolean {
  return ACTIVE_BUSY_STATUSES.has((status ?? '').trim());
}
