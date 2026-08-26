export type OperatorQuickGuideTone = 'neutral' | 'attention';

export type OperatorQuickGuideActionId =
  | 'show-terminal'
  | 'open-attention'
  | 'open-briefing'
  | 'open-connectors'
  | 'switch-to-ide';

export type OperatorQuickGuideAction = {
  id: OperatorQuickGuideActionId;
  label: string;
};

export type OperatorQuickGuide = {
  title: string;
  steps: string[];
  tone: OperatorQuickGuideTone;
  actions: OperatorQuickGuideAction[];
};

function terminalReopenSteps(): string[] {
  return [
    'Open terminal (Ctrl/Cmd+J) to follow live command output in the workbench.',
    'Header chip Open terminal, or the bottom Terminal dock strip → Show.',
  ];
}

function showTerminalAction(): OperatorQuickGuideAction {
  return { id: 'show-terminal', label: 'Open terminal' };
}

function approvalActions(): OperatorQuickGuideAction[] {
  return [
    { id: 'open-attention', label: 'Open Attention' },
    { id: 'open-briefing', label: 'Open briefing' },
  ];
}

function openConnectorsAction(): OperatorQuickGuideAction {
  return { id: 'open-connectors', label: 'Open connectors' };
}

function requiredConnectorSteps(count: number): string[] {
  const noun = count === 1 ? 'required connector' : 'required connectors';
  return [
    `Mission Control → Connectors shows ${count} ${noun} down with live probe status.`,
    'Reprobe after fixing credentials, network, or the downstream service.',
    'Refresh summary when multiple probes look stale.',
    'Left → Attention for connector failure signals in the inbox.',
  ];
}

function requiredConnectorActions(terminalVisible: boolean): OperatorQuickGuideAction[] {
  const actions: OperatorQuickGuideAction[] = [openConnectorsAction()];
  if (!terminalVisible) {
    actions.push(showTerminalAction());
  }
  actions.push({ id: 'switch-to-ide', label: 'Switch to IDE' });
  return actions;
}

function legacyConnectorSteps(): string[] {
  return [
    'Status bar connector chip opens Mission Control connectors — optional; Axon-X is healthy.',
    'Use Reprobe after fixing credentials, network, or the downstream service.',
  ];
}

function idleActions(
  terminalVisible: boolean,
  legacyConnectorGlanceVisible: boolean,
): OperatorQuickGuideAction[] {
  const actions: OperatorQuickGuideAction[] = [];
  if (legacyConnectorGlanceVisible) {
    actions.push(openConnectorsAction());
  }
  if (!terminalVisible) {
    actions.push(showTerminalAction());
  }
  actions.push({ id: 'switch-to-ide', label: 'Switch to IDE' });
  return actions;
}

export function buildOperatorQuickGuide(input: {
  runPhase: string | null;
  hasActiveRun: boolean;
  pendingApprovals: number;
  layoutMode: 'operator' | 'ide';
  terminalVisible: boolean;
  legacyConnectorGlanceVisible?: boolean;
  requiredConnectorsUnavailable?: number;
  watchConnected?: boolean;
}): OperatorQuickGuide | null {
  const legacyConnectorGlanceVisible = input.legacyConnectorGlanceVisible ?? false;
  const requiredConnectorsUnavailable = input.requiredConnectorsUnavailable ?? 0;
  const watchConnected = input.watchConnected ?? true;
  if (input.layoutMode !== 'operator') {
    return null;
  }

  if (input.pendingApprovals > 0) {
    const actions = approvalActions();
    if (!input.terminalVisible) {
      actions.push(showTerminalAction());
    }
    return {
      title: 'Approval waiting — decide before more work runs',
      tone: 'attention',
      actions,
      steps: [
        'Center Mission Control → APPROVE RUN or REJECT RUN.',
        'Left sidebar → Attention to read why approval was requested.',
        'Right dock → KAIRO Briefing for the short summary.',
        ...(input.terminalVisible ? [] : terminalReopenSteps()),
      ],
    };
  }

  if (!watchConnected && !input.hasActiveRun) {
    const actions: OperatorQuickGuideAction[] = [openConnectorsAction()];
    if (!input.terminalVisible) {
      actions.push(showTerminalAction());
    }
    actions.push({ id: 'switch-to-ide', label: 'Switch to IDE' });
    return {
      title: 'Watch offline — connector probes paused',
      tone: 'attention',
      actions,
      steps: [
        'Watch offline — connector probes paused until the watch reconnects.',
        'Mission Control → Connectors shows live status once the stack is back up.',
        'Refresh summary after ./scripts/dev/up.sh is healthy again.',
        ...(input.terminalVisible ? [] : terminalReopenSteps()),
      ],
    };
  }

  if (requiredConnectorsUnavailable > 0) {
    const count = requiredConnectorsUnavailable;
    return {
      title:
        count === 1
          ? 'Required connector down — restore the watch lane'
          : `${count} required connectors down — restore the watch lane`,
      tone: 'attention',
      actions: requiredConnectorActions(input.terminalVisible),
      steps: [
        ...requiredConnectorSteps(count),
        ...(input.terminalVisible ? [] : terminalReopenSteps()),
      ],
    };
  }

  if (input.runPhase === 'review_ready') {
    const actions: OperatorQuickGuideAction[] = [];
    if (!input.terminalVisible) {
      actions.push(showTerminalAction());
    }
    actions.push({ id: 'switch-to-ide', label: 'Switch to IDE' });
    return {
      title: input.terminalVisible
        ? 'Review ready — read output, then complete'
        : 'Review ready — open the terminal to read command output',
      tone: 'attention',
      actions,
      steps: [
        ...(input.terminalVisible ? [] : terminalReopenSteps()),
        'Read the Conversation panel (right) for command output — e.g. git status results.',
        'Center → COMPLETE RUN when the output looks good (one-shot commands do not need RESUME).',
        'For multi-step work only: RESUME RUN or type resume from review in Command.',
        'Left → Attention when signals still need review.',
      ],
    };
  }

  if (input.runPhase === 'executing') {
    const actions: OperatorQuickGuideAction[] = [];
    if (!input.terminalVisible) {
      actions.push(showTerminalAction());
    }
    return {
      title: input.terminalVisible
        ? 'Run in progress'
        : 'Run in progress — open the terminal to follow shell output',
      tone: input.terminalVisible ? 'neutral' : 'attention',
      actions,
      steps: [
        ...(input.terminalVisible ? [] : terminalReopenSteps()),
        'Watch Mission Control live feed for step-by-step progress.',
        'CONTINUE RUN when the agent is idle but the task is unfinished (stuck execute).',
        'COMPLETE RUN only after review_ready — when the work unit is truly done.',
        'STOP RUN pauses execution; RESUME continues from paused.',
        'Send more work via right dock → Command (exact commands only).',
      ],
    };
  }

  if (input.runPhase === 'paused') {
    return {
      title: 'Run paused — finish or continue',
      tone: 'neutral',
      actions: input.terminalVisible ? [] : [showTerminalAction()],
      steps: [
        ...(input.terminalVisible ? [] : terminalReopenSteps()),
        'RESUME continues the run (EXECUTE phase).',
        'Another STOP while paused cancels the run entirely.',
        'COMPLETE RUN is available after the run reaches review_ready.',
      ],
    };
  }

  if (input.runPhase === 'awaiting_approval') {
    return {
      title: 'Run waiting on approval',
      tone: 'attention',
      actions: approvalActions(),
      steps: [
        'Open Attention (left) or KAIRO Briefing (right) for context.',
        'Use APPROVE RUN / REJECT RUN in Mission Control when ready.',
      ],
    };
  }

  if (!input.hasActiveRun) {
    if (legacyConnectorGlanceVisible) {
      return {
        title: 'Optional connector is offline — Axon-X stack is healthy',
        tone: 'neutral',
        actions: idleActions(input.terminalVisible, true),
        steps: [
          ...legacyConnectorSteps(),
          ...(input.terminalVisible ? [] : terminalReopenSteps()),
          'Left sidebar → pick axon-watch or DashPro.',
          'Right dock → Command tab → try git status or health.',
          'Toggle IDE (top-right) when you need files, editor, or terminal.',
        ],
      };
    }

    return {
      title: input.terminalVisible
        ? 'Idle — start with a workspace command'
        : 'Terminal hidden — reopen when you need shell output',
      tone: 'neutral',
      actions: idleActions(input.terminalVisible, false),
      steps: [
        ...(input.terminalVisible ? [] : terminalReopenSteps()),
        'Left sidebar → pick axon-watch or DashPro.',
        'Right dock → Command tab → try git status or health.',
        'Footer Commands lists every supported command with a Use button.',
        'Toggle IDE (top-right) when you need files, editor, or terminal.',
      ],
    };
  }

  return null;
}
