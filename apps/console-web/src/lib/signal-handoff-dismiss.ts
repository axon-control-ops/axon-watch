export type InboxSignalRef = {
  signal_id: string;
};

export const PENDING_HANDOFF_DISMISS_KEY = 'axon-x:pending-handoff-signal-dismiss-v1';

export function isMonitorSignalId(signalId: string): boolean {
  return signalId.trim().startsWith('signal_monitor_');
}

export function linkedMonitorCheckId(signalId: string): string | null {
  const match = /^signal_monitor_(.+)_(critical|warning)$/.exec(signalId.trim());
  return match?.[1] ?? null;
}

export function monitorSignalIdsForCheck(checkId: string): string[] {
  const base = checkId.trim();
  if (!base) {
    return [];
  }

  return [`signal_monitor_${base}_critical`, `signal_monitor_${base}_warning`];
}

export function isSignalOpenInInbox(
  signalId: string,
  inboxItems: InboxSignalRef[],
): boolean {
  const normalized = signalId.trim();
  if (!normalized) {
    return false;
  }

  return inboxItems.some((item) => item.signal_id === normalized);
}

export function canVerifyDismissHandoffSignal(
  signalId: string,
  inboxItems: InboxSignalRef[],
): { allowed: boolean; reason?: string } {
  const normalized = signalId.trim();
  if (!normalized) {
    return { allowed: false, reason: 'No signal selected.' };
  }

  if (!isMonitorSignalId(normalized)) {
    return { allowed: true };
  }

  if (isSignalOpenInInbox(normalized, inboxItems)) {
    return {
      allowed: false,
      reason:
        'Monitor still reports this issue. Resolve the Sentry issue(s) below, deploy the fix, wait for the monitor to clear, or use CLEAR to acknowledge locally.',
    };
  }

  return { allowed: true };
}

export function readPendingHandoffDismissSignalId(): string | null {
  if (typeof sessionStorage === 'undefined') {
    return null;
  }

  const value = sessionStorage.getItem(PENDING_HANDOFF_DISMISS_KEY)?.trim();
  return value || null;
}

export function writePendingHandoffDismissSignalId(signalId: string | null): void {
  if (typeof sessionStorage === 'undefined') {
    return;
  }

  const normalized = signalId?.trim() ?? '';
  if (!normalized) {
    sessionStorage.removeItem(PENDING_HANDOFF_DISMISS_KEY);
    return;
  }

  sessionStorage.setItem(PENDING_HANDOFF_DISMISS_KEY, normalized);
}
