import {
  OPERATOR_FAILURE_CONTINUE_LABEL,
  OPERATOR_FAILURE_RETRY_LABEL,
} from './operator-failure-copy';

export type IdeSidebarStubTone =
  | 'neutral'
  | 'attention'
  | 'streaming'
  | 'failure'
  | 'interrupted';

export type IdeSidebarStubActionKind = 'toggle_agent_dock' | 'open_team';

export type IdeSidebarStubPanel = {
  lines: string[];
  actionLabel: string | null;
  actionKind?: IdeSidebarStubActionKind;
  /** Optional second CTA — e.g. Try again when the dock stays collapsed. */
  secondaryActionLabel?: string | null;
  tone: IdeSidebarStubTone;
};

/** Whether agent/terminal stub copy should announce through a live region. */
export function ideSidebarStubUsesLiveRegion(
  tone: IdeSidebarStubTone,
  scope: 'agent' | 'terminal',
): boolean {
  if (scope === 'terminal') {
    return tone === 'attention';
  }

  return tone !== 'neutral';
}

/** Descriptive label for stub CTA buttons (visible text stays short). */
export function ideSidebarStubActionAriaLabel(
  actionLabel: string,
  scope: 'agent' | 'terminal',
): string {
  if (scope === 'agent') {
    if (actionLabel === 'Expand agent dock') {
      return 'Expand agent dock on the right edge';
    }
    if (actionLabel === 'Collapse agent dock') {
      return 'Collapse agent dock on the right edge';
    }
    if (actionLabel === 'Open Team roster') return 'Open Team roster in the left sidebar';
  }

  if (scope === 'terminal') {
    if (actionLabel === 'Show terminal') {
      return 'Show terminal panel below the editor';
    }
    if (actionLabel === 'Hide terminal') {
      return 'Hide terminal panel below the editor';
    }
  }

  if (actionLabel === OPERATOR_FAILURE_RETRY_LABEL) {
    return 'Try again from the agent dock composer';
  }
  if (actionLabel === OPERATOR_FAILURE_CONTINUE_LABEL) {
    return 'Continue from the agent dock composer';
  }

  return actionLabel;
}

function approvalPhrase(count: number): string {
  return `${count} approval${count === 1 ? '' : 's'} waiting`;
}

function employeeFailureSidebarStep(interrupted: boolean): string {
  return interrupted
    ? 'Expand the dock, then open Team and tap Continue on their roster card.'
    : 'Expand the dock, then open Team and tap Try again on their roster card.';
}

/** Copy and CTA for the IDE left-rail agent stub when the dock lives on the right. */
export function buildIdeAgentSidebarStub(input: {
  agentDockCollapsed: boolean;
  streaming: boolean;
  pendingApprovals: number;
  runPhase: string | null;
  employeeFailureLine?: string | null;
  employeeShiftInterrupted?: boolean;
  employeeRetryActionLabel?: string | null;
}): IdeSidebarStubPanel {
  if (!input.agentDockCollapsed) {
    return {
      tone: 'neutral',
      lines: [
        'Agent dock is open on the right edge.',
        'Use Team for teammate status/action cards and dispatch follow-up.',
      ],
      actionLabel: 'Open Team roster',
      actionKind: 'open_team',
    };
  }

  if (input.pendingApprovals > 0) {
    return {
      tone: 'attention',
      lines: [
        `${approvalPhrase(input.pendingApprovals)} in the agent dock.`,
        'Expand the dock to review and approve before more agent work runs.',
        'Ctrl/Cmd+\\ · editor status bar AGENT chip · right-edge reopen strip.',
      ],
      actionLabel: 'Expand agent dock',
      actionKind: 'toggle_agent_dock',
    };
  }

  if (input.streaming) {
    return {
      tone: 'streaming',
      lines: [
        'Agent is responding — expand the dock to follow the conversation.',
        'Ctrl/Cmd+\\ · editor status bar · right-edge reopen strip.',
      ],
      actionLabel: 'Expand agent dock',
      actionKind: 'toggle_agent_dock',
    };
  }

  const failureLine = (input.employeeFailureLine ?? '').trim();
  const idleRun = input.runPhase !== 'executing' && input.runPhase !== 'review_ready';
  if (failureLine && idleRun) {
    const interrupted = Boolean(input.employeeShiftInterrupted);
    const retryLabel = (input.employeeRetryActionLabel ?? '').trim();
    return {
      tone: interrupted ? 'interrupted' : 'failure',
      lines: [
        failureLine,
        employeeFailureSidebarStep(interrupted),
        'Ctrl/Cmd+\\ · editor status bar AGENT chip · right-edge reopen strip.',
      ],
      actionLabel: 'Expand agent dock',
      actionKind: 'toggle_agent_dock',
      secondaryActionLabel: retryLabel || null,
    };
  }

  if (input.runPhase === 'review_ready') {
    return {
      tone: 'neutral',
      lines: [
        'Review ready — expand the dock to read command output.',
        'Ctrl/Cmd+\\ · editor status bar AGENT chip · right-edge reopen strip.',
      ],
      actionLabel: 'Expand agent dock',
      actionKind: 'toggle_agent_dock',
    };
  }

  if (input.runPhase === 'executing') {
    return {
      tone: 'neutral',
      lines: [
        'Run in progress — expand the dock to follow along.',
        'Ctrl/Cmd+\\ · editor status bar AGENT chip · right-edge reopen strip.',
      ],
      actionLabel: 'Expand agent dock',
      actionKind: 'toggle_agent_dock',
    };
  }

  return {
    tone: 'neutral',
    lines: [
      'Agent dock is collapsed on the right.',
      'Ctrl/Cmd+\\ expands it for conversation and composer.',
    ],
    actionLabel: 'Expand agent dock',
    actionKind: 'toggle_agent_dock',
  };
}

export type IdeRunPanelConnectorNotice = {
  lines: string[];
  actionLabel: string;
  tone: 'neutral' | 'attention';
};

/** Watch-lane connector notice for the IDE Run sidebar when probes need attention. */
export function buildIdeRunPanelConnectorNotice(input: {
  watchConnected: boolean;
  requiredConnectorsUnavailable: number;
  legacyConnectorGlanceVisible: boolean;
}): IdeRunPanelConnectorNotice | null {
  if (!input.watchConnected) {
    return {
      tone: 'attention',
      lines: [
        'Watch offline — connector probes paused until the watch reconnects.',
        'Mission Control → Connectors shows live status once the stack is back up.',
        'Editor status bar WATCH OFFLINE chip · footer chip · Run activity pulse.',
      ],
      actionLabel: 'Open connectors',
    };
  }

  const required = input.requiredConnectorsUnavailable;
  if (required > 0) {
    return {
      tone: 'attention',
      lines: [
        required === 1
          ? '1 required connector down — restore the watch lane before more work.'
          : `${required} required connectors down — restore the watch lane before more work.`,
        'Mission Control → Connectors for live probe status and reprobe.',
        'Editor status bar chip · footer status bar chip · quick guide Open connectors.',
      ],
      actionLabel: 'Open connectors',
    };
  }

  if (input.legacyConnectorGlanceVisible) {
    return {
      tone: 'neutral',
      lines: [
        'Legacy Axon Local is offline — Axon-X stack is healthy.',
        'Optional connector only — reprobe or open :7734 fallback when needed.',
        'Editor status bar LEGACY OFFLINE chip · footer chip · quick guide Open connectors.',
      ],
      actionLabel: 'Open connectors',
    };
  }

  return null;
}

/** Copy and CTA for the IDE left-rail terminal stub when the panel lives in the workbench. */
export function buildIdeTerminalSidebarStub(input: {
  terminalVisible: boolean;
  runPhase: string | null;
}): IdeSidebarStubPanel {
  if (input.terminalVisible) {
    return {
      tone: 'neutral',
      lines: [
        'Terminal panel is open below the editor.',
        'Ctrl/Cmd+J hides it when you want a cleaner workbench.',
      ],
      actionLabel: 'Hide terminal',
    };
  }

  const runNeedsTerminal =
    input.runPhase === 'executing' || input.runPhase === 'review_ready';

  return {
    tone: runNeedsTerminal ? 'attention' : 'neutral',
    lines: [
      input.runPhase === 'executing'
        ? 'Run in progress — show the terminal to follow shell output.'
        : input.runPhase === 'review_ready'
          ? 'Review ready — show the terminal to read command output.'
          : 'Terminal panel is hidden.',
      'Ctrl/Cmd+J · editor status bar TERMINAL chip · bottom reopen strip.',
    ],
    actionLabel: 'Show terminal',
  };
}
