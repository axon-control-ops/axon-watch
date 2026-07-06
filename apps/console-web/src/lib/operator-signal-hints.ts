/** Plain-language operator hints for inbox / briefing signals. */

const BOOTSTRAP_SUMMARY_SIGNAL_IDS = new Set([
  'signal_runtime_summary_degraded',
]);

export function isBootstrapSummarySignal(signalId: string, title: string): boolean {
  return (
    BOOTSTRAP_SUMMARY_SIGNAL_IDS.has(signalId) ||
    title.toLowerCase().includes('bootstrap') ||
    title.toLowerCase().includes('runtime summary stale')
  );
}

export function signalOperatorHint(input: {
  signalId: string;
  title: string;
  summary?: string | null;
  meta?: Record<string, unknown> | null;
}): string {
  const signalFamily = String(input.meta?.signal_family ?? '');
  if (signalFamily === 'child_project_monitor') {
    const workspaceLabel = String(input.meta?.workspace_label ?? 'Child project');
    const monitorStatus = String(input.meta?.monitor_status ?? 'issue');
    return (
      `${workspaceLabel} monitor reported ${monitorStatus}. ` +
      'Review the external service dashboard. Missing credentials can be imported on /vault.'
    );
  }

  if (isBootstrapSummarySignal(input.signalId, input.title)) {
    return (
      'Expected in local bootstrap dev — not a production outage. Watch is connected; ' +
      'runtime summary data is still intentionally thin. No repair step: you can ignore this ' +
      'or continue with Command (health, git status, etc.).'
    );
  }

  if (input.summary?.trim()) {
    return input.summary.trim();
  }

  return 'Review this signal for context. Automated signal actions are not wired in operator v1 yet.';
}

export function watchRuleLabel(mode: string | undefined): string {
  switch ((mode ?? 'observe').toLowerCase()) {
    case 'observe':
      return 'Observe';
    case 'advise':
      return 'Advise';
    case 'approval':
      return 'Approval';
    case 'execute':
      return 'Execute';
    default:
      return mode ?? 'Observe';
  }
}

export function watchRuleTooltip(mode: string | undefined): string {
  switch ((mode ?? 'observe').toLowerCase()) {
    case 'observe':
      return 'KAIRO watch mode: observe — informational only, no click action required.';
    case 'advise':
      return 'KAIRO watch mode: advise — suggestion only; use Mission Control or Command.';
    case 'approval':
      return 'KAIRO watch mode: approval — requires explicit approve/reject.';
    case 'execute':
      return 'KAIRO watch mode: execute — may interrupt; review in Mission Control.';
    default:
      return 'KAIRO watch rule mode (status label, not a button).';
  }
}

export function deliveryStateLabel(state: string | undefined): string {
  if (!state || state === 'not_required') {
    return '';
  }
  if (state === 'delivered') {
    return 'Delivered';
  }
  return state.charAt(0).toUpperCase() + state.slice(1);
}

export function deliveryStateTooltip(state: string | undefined): string {
  if (state === 'delivered') {
    return 'Delivery receipt recorded (read-only status, not a button).';
  }
  if (state === 'pending') {
    return 'Delivery pending (read-only status).';
  }
  return 'Signal delivery state (read-only status, not a button).';
}
