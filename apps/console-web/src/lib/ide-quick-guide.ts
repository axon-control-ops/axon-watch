export type IdeQuickGuideTone =
  | 'neutral'
  | 'attention'
  | 'streaming'
  | 'failure'
  | 'interrupted';

export type IdeQuickGuideActionId =
  | 'expand-agent-dock'
  | 'show-terminal'
  | 'open-connectors'
  | 'retry-employee-shift'
  | 'view-employee-receipts'
  | 'open-team-roster';

export type IdeQuickGuideAction = {
  id: IdeQuickGuideActionId;
  label: string;
};

export type IdeQuickGuide = {
  title: string;
  steps: string[];
  tone: IdeQuickGuideTone;
  actions: IdeQuickGuideAction[];
};

function withEmployeeFailureDetail(
  line: string | null | undefined,
  steps: string[],
): string[] {
  const detail = (line ?? '').trim();
  return detail ? [detail, ...steps] : steps;
}

function employeeFailureBannerStep(interrupted: boolean): string {
  const action = interrupted ? 'Continue shift' : 'Retry shift';
  return interrupted
    ? `Use ${action} in the failure banner to continue, or open Team to talk it through.`
    : `Use ${action} in the failure banner, or open Team to talk it through.`;
}

function employeeFailureComposerBannerStep(interrupted: boolean): string {
  const action = interrupted ? 'Continue shift' : 'Retry shift';
  return `Use ${action} in the failure banner at the top of the agent dock composer.`;
}

function employeeFailureCollapsedDockSteps(input: {
  interrupted: boolean;
  employeeRetryActionLabel?: string | null;
  employeeHasReceipts?: boolean;
}): string[] {
  const retryLabel = (input.employeeRetryActionLabel ?? '').trim();
  if (retryLabel) {
    const steps = [
      `Click ${retryLabel} above to open the agent dock with a prefilled composer.`,
    ];
    if (input.employeeHasReceipts) {
      steps.push('View receipts above to inspect the last run output.');
    }
    steps.push(
      'Open Team to review the roster or talk it through.',
      'Ctrl/Cmd+\\ also toggles the agent dock; the failure banner appears at the top of the composer.',
    );
    return steps;
  }

  return [
    'Ctrl/Cmd+\\ toggles the agent dock.',
    employeeFailureBannerStep(input.interrupted),
    'Click AGENT in the editor status bar or the right-edge reopen strip.',
  ];
}

function employeeFailureOpenDockStep(input: {
  interrupted: boolean;
  employeeRetryActionLabel?: string | null;
}): string {
  const retryLabel = (input.employeeRetryActionLabel ?? '').trim();
  if (retryLabel) {
    return `Click ${retryLabel} above, or use the failure banner at the top of the agent dock composer.`;
  }

  return employeeFailureComposerBannerStep(input.interrupted);
}

function employeeFailureQuickGuideActions(input: {
  agentDockCollapsed: boolean;
  terminalVisible: boolean;
  employeeRetryActionLabel?: string | null;
  employeeHasReceipts?: boolean;
}): IdeQuickGuideAction[] {
  const retryLabel = (input.employeeRetryActionLabel ?? '').trim();
  const actions: IdeQuickGuideAction[] = [];

  if (retryLabel) {
    actions.push({ id: 'retry-employee-shift', label: retryLabel });
    if (input.employeeHasReceipts) {
      actions.push({ id: 'view-employee-receipts', label: 'View receipts' });
    }
  } else if (input.agentDockCollapsed) {
    actions.push({ id: 'expand-agent-dock', label: 'Expand agent dock' });
  }

  actions.push({ id: 'open-team-roster', label: 'Open team' });

  if (!input.terminalVisible) {
    actions.push({ id: 'show-terminal', label: 'Show terminal' });
  }

  return actions;
}

export function buildIdeQuickGuide(input: {
  layoutMode: 'operator' | 'ide';
  agentDockCollapsed: boolean;
  terminalVisible: boolean;
  pendingApprovals: number;
  streaming: boolean;
  runPhase: string | null;
  employeeFailureLine?: string | null;
  employeeShiftInterrupted?: boolean;
  employeeRetryActionLabel?: string | null;
  employeeHasReceipts?: boolean;
  requiredConnectorsUnavailable?: number;
  legacyConnectorGlanceVisible?: boolean;
  watchConnected?: boolean;
}): IdeQuickGuide | null {
  if (input.layoutMode !== 'ide') {
    return null;
  }

  const requiredConnectorsUnavailable = input.requiredConnectorsUnavailable ?? 0;
  const legacyConnectorGlanceVisible = input.legacyConnectorGlanceVisible ?? false;
  const watchConnected = input.watchConnected ?? true;
  const idleRun = input.runPhase !== 'executing' && input.runPhase !== 'review_ready';

  if (input.pendingApprovals > 0 && input.agentDockCollapsed) {
    return {
      title: 'Approval waiting in the agent dock',
      tone: 'attention',
      actions: [{ id: 'expand-agent-dock', label: 'Expand agent dock' }],
      steps: [
        'Press Ctrl/Cmd+\\ or click AGENT in the editor status bar to expand the dock.',
        'Review the approval request in the conversation thread.',
        'Approve or reject before more agent work runs.',
      ],
    };
  }

  if (input.streaming && input.agentDockCollapsed) {
    return {
      title: 'Agent is responding — expand the dock to follow along',
      tone: 'streaming',
      actions: [{ id: 'expand-agent-dock', label: 'Expand agent dock' }],
      steps: [
        'Ctrl/Cmd+\\ toggles the agent dock.',
        'Click AGENT in the editor status bar or the right-edge reopen strip.',
      ],
    };
  }

  if (input.agentDockCollapsed && (input.employeeFailureLine ?? '').trim()) {
    const interrupted = Boolean(input.employeeShiftInterrupted);
    const retryLabel = (input.employeeRetryActionLabel ?? '').trim();
    return {
      title: retryLabel
        ? interrupted
          ? 'Shift interrupted — continue from the quick guide'
          : 'Last shift failed — retry from the quick guide'
        : interrupted
          ? 'Shift interrupted — expand the agent dock to continue'
          : 'Last shift failed — expand the agent dock to retry',
      tone: interrupted ? 'interrupted' : 'failure',
      actions: employeeFailureQuickGuideActions({
        agentDockCollapsed: true,
        terminalVisible: input.terminalVisible,
        employeeRetryActionLabel: input.employeeRetryActionLabel,
        employeeHasReceipts: input.employeeHasReceipts,
      }),
      steps: withEmployeeFailureDetail(
        input.employeeFailureLine,
        employeeFailureCollapsedDockSteps({
          interrupted,
          employeeRetryActionLabel: input.employeeRetryActionLabel,
          employeeHasReceipts: input.employeeHasReceipts,
        }),
      ),
    };
  }

  if (
    !input.agentDockCollapsed &&
    (input.employeeFailureLine ?? '').trim() &&
    idleRun &&
    !input.streaming &&
    input.pendingApprovals <= 0
  ) {
    const interrupted = Boolean(input.employeeShiftInterrupted);

    return {
      title: interrupted
        ? 'Shift interrupted — retry from the agent dock banner'
        : 'Last shift failed — retry from the agent dock banner',
      tone: interrupted ? 'interrupted' : 'failure',
      actions: employeeFailureQuickGuideActions({
        agentDockCollapsed: false,
        terminalVisible: input.terminalVisible,
        employeeRetryActionLabel: input.employeeRetryActionLabel,
        employeeHasReceipts: input.employeeHasReceipts,
      }),
      steps: withEmployeeFailureDetail(input.employeeFailureLine, [
        employeeFailureOpenDockStep({
          interrupted,
          employeeRetryActionLabel: input.employeeRetryActionLabel,
        }),
        'Open Team in the left sidebar to review receipts or talk it through.',
        ...(input.terminalVisible
          ? []
          : ['Ctrl/Cmd+J opens the terminal when you need shell output in the workbench.']),
      ]),
    };
  }

  if (idleRun && !watchConnected) {
    const actions: IdeQuickGuideAction[] = [{ id: 'open-connectors', label: 'Open connectors' }];
    if (!input.terminalVisible) {
      actions.push({ id: 'show-terminal', label: 'Show terminal' });
    }

    return {
      title: 'Watch offline — connector probes paused',
      tone: 'attention',
      actions,
      steps: [
        'Runtime probes pause until the watch reconnects.',
        'Mission Control → Connectors shows live status once the stack is back up.',
        'Refresh summary after the dev stack is healthy again.',
        ...(input.terminalVisible
          ? []
          : ['Ctrl/Cmd+J opens the terminal when you need shell output in the workbench.']),
      ],
    };
  }

  if (idleRun && requiredConnectorsUnavailable > 0) {
    const count = requiredConnectorsUnavailable;
    const actions: IdeQuickGuideAction[] = [{ id: 'open-connectors', label: 'Open connectors' }];
    if (!input.terminalVisible) {
      actions.push({ id: 'show-terminal', label: 'Show terminal' });
    }

    return {
      title:
        count === 1
          ? 'Required connector down — restore the watch lane'
          : `${count} required connectors down — restore the watch lane`,
      tone: 'attention',
      actions,
      steps: [
        'Switch to Mission Control → Connectors for live probe status and reprobe actions.',
        'Reprobe after fixing credentials, network, or the downstream service.',
        'Editor status bar chip · footer status bar chip · quick guide Open connectors.',
        ...(input.terminalVisible
          ? []
          : ['Ctrl/Cmd+J opens the terminal when you need shell output in the workbench.']),
      ],
    };
  }

  if (idleRun && legacyConnectorGlanceVisible) {
    const actions: IdeQuickGuideAction[] = [{ id: 'open-connectors', label: 'Open connectors' }];
    if (!input.terminalVisible) {
      actions.push({ id: 'show-terminal', label: 'Show terminal' });
    }

    return {
      title: 'Legacy Axon Local is offline — Axon-X stack is healthy',
      tone: 'neutral',
      actions,
      steps: [
        'Editor status bar LEGACY OFFLINE chip · footer chip · quick guide Open connectors.',
        'Optional connector only — reprobe or open the :7734 fallback when you still need classic Axon Local.',
        ...(input.terminalVisible
          ? []
          : ['Ctrl/Cmd+J opens the terminal when you need shell output in the workbench.']),
      ],
    };
  }

  if (
    input.agentDockCollapsed &&
    (input.runPhase === 'executing' || input.runPhase === 'review_ready')
  ) {
    const actions: IdeQuickGuideAction[] = [
      { id: 'expand-agent-dock', label: 'Expand agent dock' },
    ];
    const steps = [
      'Ctrl/Cmd+\\ toggles the agent dock.',
      'Click AGENT in the editor status bar or the right-edge reopen strip.',
      ...(input.runPhase === 'review_ready'
        ? ['Read command output in the conversation panel, then complete the run when ready.']
        : ['Watch live progress and steer from the composer when needed.']),
    ];
    if (!input.terminalVisible) {
      actions.push({ id: 'show-terminal', label: 'Show terminal' });
      steps.push('Ctrl/Cmd+J opens the terminal panel for live shell output.');
    }

    return {
      title:
        input.runPhase === 'review_ready'
          ? 'Review ready — expand the agent dock to read output'
          : 'Run in progress — expand the agent dock to follow along',
      tone: 'neutral',
      actions,
      steps,
    };
  }

  if (!input.terminalVisible && !input.agentDockCollapsed) {
    if (input.runPhase === 'executing') {
      return {
        title: 'Run in progress — show the terminal to follow shell output',
        tone: 'attention',
        actions: [{ id: 'show-terminal', label: 'Show terminal' }],
        steps: [
          'Ctrl/Cmd+J toggles the terminal panel in the workbench.',
          'Click TERMINAL in the editor status bar, the bottom reopen strip, or the terminal icon in the left activity bar.',
          'Watch live command output while the agent dock stays open for conversation.',
        ],
      };
    }

    if (input.runPhase === 'review_ready') {
      return {
        title: 'Review ready — show the terminal to read command output',
        tone: 'attention',
        actions: [{ id: 'show-terminal', label: 'Show terminal' }],
        steps: [
          'Ctrl/Cmd+J toggles the terminal panel in the workbench.',
          'Click TERMINAL in the editor status bar, the bottom reopen strip, or the terminal icon in the left activity bar.',
          'Read shell output here; complete the run from the agent dock when ready.',
        ],
      };
    }

    return {
      title: 'Terminal hidden — reopen when you need shell output',
      tone: 'neutral',
      actions: [{ id: 'show-terminal', label: 'Show terminal' }],
      steps: [
        'Ctrl/Cmd+J toggles the terminal panel in the workbench.',
        'Click TERMINAL in the editor status bar, the bottom reopen strip, or the terminal icon in the left activity bar.',
      ],
    };
  }

  if (input.agentDockCollapsed && !input.terminalVisible) {
    return {
      title: 'Panels closed — keyboard shortcuts',
      tone: 'neutral',
      actions: [
        { id: 'expand-agent-dock', label: 'Expand agent dock' },
        { id: 'show-terminal', label: 'Show terminal' },
      ],
      steps: [
        'Ctrl/Cmd+\\ — agent dock (conversation + composer)',
        'Ctrl/Cmd+J — terminal panel in the workbench',
        'Ctrl/Cmd+B — file explorer sidebar',
        'Editor status bar chips and the left activity bar work too when you prefer clicking.',
      ],
    };
  }

  if (input.agentDockCollapsed && input.terminalVisible) {
    return {
      title: 'Agent dock collapsed — reopen for conversation',
      tone: 'neutral',
      actions: [{ id: 'expand-agent-dock', label: 'Expand agent dock' }],
      steps: [
        'Ctrl/Cmd+\\ toggles the agent dock (conversation + composer).',
        'Click AGENT in the editor status bar, the right-edge reopen strip, or the agent icon in the left activity bar.',
      ],
    };
  }

  return null;
}
