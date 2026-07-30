/** Confirm + clear helpers for Operator Task Board waiting queue. */

export async function confirmCancelAllWaiting(options: {
  waitingCount: number;
  mutating: boolean;
  cancelAll: () => Promise<number>;
}): Promise<boolean> {
  if (!options.waitingCount || options.mutating) {
    return false;
  }
  const confirmed = window.confirm(
    `Cancel all ${options.waitingCount} waiting task(s) on this workspace? Bound queued runs will stop too.`,
  );
  if (!confirmed) {
    return false;
  }
  await options.cancelAll();
  return true;
}

export async function confirmClearDuplicateWaiting(options: {
  mutating: boolean;
  clearDuplicates: () => Promise<number>;
}): Promise<boolean> {
  if (options.mutating) {
    return false;
  }
  const confirmed = window.confirm(
    'Clear waiting tasks that duplicate completed work or each other? Distinct follow-ups stay.',
  );
  if (!confirmed) {
    return false;
  }
  await options.clearDuplicates();
  return true;
}
