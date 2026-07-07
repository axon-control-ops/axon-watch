import { isBootstrapSummarySignal } from './operator-signal-hints';

export type IdeInterruptStopTarget = 'ide-agent' | 'primary' | null;

export type IdeInterruptTopSignal = {
  signal_id: string;
  title: string;
  summary?: string | null;
  severity?: string | null;
};

function isActionableInterruptSignal(signal: IdeInterruptTopSignal | null | undefined): boolean {
  if (!signal?.title) {
    return false;
  }

  if (isBootstrapSummarySignal(signal.signal_id, signal.title)) {
    return false;
  }

  const severity = (signal.severity ?? '').toLowerCase();
  return severity === 'critical' || severity === 'high' || severity === 'medium';
}

export function resolveIdeInterruptHeadline(input: {
  pendingApprovalsCount: number;
  topSignal: IdeInterruptTopSignal | null | undefined;
  watchConnected: boolean;
  degradedActive: boolean;
  primaryRunPhase: string | null | undefined;
}): string {
  if (input.pendingApprovalsCount > 0) {
    const count = input.pendingApprovalsCount;
    return `${count} approval${count === 1 ? '' : 's'} waiting for your review`;
  }

  if (!input.watchConnected) {
    return 'Watch connector offline';
  }

  if (input.degradedActive) {
    return 'Runtime degraded — attention required';
  }

  if (isActionableInterruptSignal(input.topSignal)) {
    return input.topSignal?.title ?? 'Attention required';
  }

  if (input.primaryRunPhase === 'awaiting_approval') {
    return 'Run blocked — awaiting approval';
  }

  return 'Attention required';
}

export function resolveIdeInterruptDetailLine(input: {
  pendingApprovalsCount: number;
  topSignal: IdeInterruptTopSignal | null | undefined;
  watchConnected: boolean;
  degradedActive: boolean;
  primaryRunCurrentStep: string | null | undefined;
}): string {
  if (input.pendingApprovalsCount > 0) {
    return 'Review before the agent can continue.';
  }

  if (!input.watchConnected) {
    return 'Control plane cannot reach the watch service. Run ./scripts/dev/check-health.sh or wait for runtime refresh.';
  }

  if (input.degradedActive) {
    return 'Review the status strip and briefing before continuing.';
  }

  if (isActionableInterruptSignal(input.topSignal)) {
    return input.topSignal?.summary?.trim() || 'Open Attention to review signals, approvals, or run state.';
  }

  if (input.primaryRunCurrentStep) {
    return input.primaryRunCurrentStep;
  }

  return 'Open Attention to review signals, approvals, or run state.';
}

export function shouldShowIdeInterruptAttentionAction(input: {
  pendingApprovalsCount: number;
  topSignals: IdeInterruptTopSignal[];
  degradedActive: boolean;
}): boolean {
  if (input.pendingApprovalsCount > 0) {
    return true;
  }

  if (input.degradedActive) {
    return true;
  }

  return input.topSignals.some((signal) => isActionableInterruptSignal(signal));
}

export function shouldShowIdeInterruptStop(input: {
  canStopIdeAgentRun: boolean;
  canStopPrimaryRun: boolean;
  primaryRunPhase: string | null | undefined;
  agentStreamActive: boolean;
}): boolean {
  if (input.canStopIdeAgentRun || input.agentStreamActive) {
    return true;
  }

  if (input.canStopPrimaryRun) {
    return true;
  }

  return input.primaryRunPhase === 'executing';
}

export function resolveIdeInterruptStopTarget(input: {
  canStopIdeAgentRun: boolean;
  agentStreamActive: boolean;
}): IdeInterruptStopTarget {
  if (input.canStopIdeAgentRun || input.agentStreamActive) {
    return 'ide-agent';
  }

  return 'primary';
}

export function isIdeInterruptStopDisabled(input: {
  runMutationStopping: boolean;
  canStopIdeAgentRun: boolean;
  canStopPrimaryRun: boolean;
  primaryRunPhase: string | null | undefined;
}): boolean {
  if (input.runMutationStopping) {
    return true;
  }

  if (input.canStopIdeAgentRun) {
    return false;
  }

  return !input.canStopPrimaryRun && input.primaryRunPhase !== 'executing';
}
