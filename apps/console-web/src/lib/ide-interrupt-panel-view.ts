export type IdeInterruptStopTarget = 'ide-agent' | 'primary' | null;

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
