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

export type IdeSidebarStubPanel = {
  lines: string[];
  actionLabel: string | null;
  tone: IdeSidebarStubTone;
};

/** Whether terminal stub copy should announce through a live region. */
export function ideSidebarStubUsesLiveRegion(
  tone: IdeSidebarStubTone,
  scope: 'agent' | 'terminal',
): boolean {
  if (scope === 'terminal') {
    return tone === 'attention';
  }

  return tone !== 'neutral';
}

/** Descriptive label for stub and quick-guide CTA buttons (visible text stays short). */
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
