export type IdeSidebarStubTone = 'neutral' | 'attention' | 'streaming';

export type IdeSidebarStubPanel = {
  lines: string[];
  actionLabel: string | null;
  tone: IdeSidebarStubTone;
};

function approvalPhrase(count: number): string {
  return `${count} approval${count === 1 ? '' : 's'} waiting`;
}

/** Copy and CTA for the IDE left-rail agent stub when the dock lives on the right. */
export function buildIdeAgentSidebarStub(input: {
  agentDockCollapsed: boolean;
  streaming: boolean;
  pendingApprovals: number;
  runPhase: string | null;
}): IdeSidebarStubPanel {
  if (!input.agentDockCollapsed) {
    return {
      tone: 'neutral',
      lines: [
        'Agent dock is open on the right edge.',
        'Ctrl/Cmd+\\ collapses it when you need more editor space.',
      ],
      actionLabel: 'Collapse agent dock',
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
    };
  }

  return {
    tone: 'neutral',
    lines: [
      'Agent dock is collapsed on the right.',
      'Ctrl/Cmd+\\ expands it for conversation and composer.',
    ],
    actionLabel: 'Expand agent dock',
  };
}

export type IdeRunPanelConnectorNotice = {
  lines: string[];
  actionLabel: string;
  tone: 'neutral' | 'attention';
};

/** Watch-lane connector notice for the IDE Run sidebar when probes need attention. */
export function buildIdeRunPanelConnectorNotice(input: {
  requiredConnectorsUnavailable: number;
  legacyConnectorGlanceVisible: boolean;
}): IdeRunPanelConnectorNotice | null {
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
