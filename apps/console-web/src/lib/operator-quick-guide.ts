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
    'Status bar chip LEGACY AXON LOCAL OFFLINE opens Mission Control connectors — optional; Axon-X is healthy.',
    'Use Reprobe or Open :7734 fallback when you still need classic Axon Local.',
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
}): OperatorQuickGuide | null {
  const legacyConnectorGlanceVisible = input.legacyConnectorGlanceVisible ?? false;
  const requiredConnectorsUnavailable = input.requiredConnectorsUnavailable ?? 0;
  if (input.layoutMode !== 'operator') {
    return null;
  }

  if (input.pendingApprovals > 0) {
    return {
      title: 'Approval waiting — decide before more work runs',
      tone: 'attention',
      actions: approvalActions(),
      steps: [
        'Center Mission Control → APPROVE RUN or REJECT RUN.',
        'Left sidebar → Attention to read why approval was requested.',
        'Right dock → KAIRO Briefing for the short summary.',
      ],
    };
  }

  if (input.runPhase === 'review_ready') {
    return {
      title: input.terminalVisible
        ? 'Review ready — read output, then complete'
        : 'Review ready — open terminal to read output',
      tone: 'neutral',
      actions: input.terminalVisible ? [] : [showTerminalAction()],
      steps: [
        ...(input.terminalVisible ? [] : terminalReopenSteps()),
        'Read the Conversation panel (right) for command output — e.g. git status results.',
        ...(input.terminalVisible
          ? ['Open terminal (Ctrl/Cmd+J) when you need raw shell output in the center workbench.']
          : []),
        'Center → COMPLETE RUN when the output looks good (one-shot commands do not need RESUME).',
        'For multi-step work only: RESUME RUN or type resume from review in Command.',
        'Left → Attention when signals still need review.',
      ],
    };
  }

  if (input.runPhase === 'executing') {
    return {
      title: input.terminalVisible
        ? 'Run in progress'
        : 'Run in progress — terminal hidden',
      tone: 'neutral',
      actions: input.terminalVisible ? [] : [showTerminalAction()],
      steps: [
        ...(input.terminalVisible ? [] : terminalReopenSteps()),
        'Watch Mission Control live feed for step-by-step progress.',
        ...(input.terminalVisible
          ? ['Open terminal (Ctrl/Cmd+J) to follow live command output in the workbench.']
          : []),
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
      actions: [],
      steps: [
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
    if (requiredConnectorsUnavailable > 0) {
      const count = requiredConnectorsUnavailable;
      return {
        title:
          count === 1
            ? 'Required connector down — restore watch lane before more work'
            : `${count} required connectors down — restore watch lane`,
        tone: 'attention',
        actions: requiredConnectorActions(input.terminalVisible),
        steps: [
          ...requiredConnectorSteps(count),
          ...(input.terminalVisible
            ? []
            : ['Open terminal (Ctrl/Cmd+J) when you need shell output in the workbench.']),
        ],
      };
    }

    if (!input.terminalVisible) {
      return {
        title: legacyConnectorGlanceVisible
          ? 'Terminal hidden — legacy Axon Local is offline'
          : 'Terminal hidden — reopen when you need shell output',
        tone: 'neutral',
        actions: idleActions(false, legacyConnectorGlanceVisible),
        steps: [
          'Header chip Open terminal, or the bottom Terminal dock strip → Show.',
          'Ctrl/Cmd+J toggles the terminal panel from anywhere in Operator mode.',
          ...(legacyConnectorGlanceVisible ? legacyConnectorSteps() : []),
          'Left sidebar → pick a workspace; Right dock → Command for health or git status.',
          'Toggle IDE (top-right) for files, editor, and agent dock (Ctrl/Cmd+\\).',
        ],
      };
    }

    return {
      title: legacyConnectorGlanceVisible
        ? 'Idle — legacy Axon Local is offline'
        : 'Idle — start with a workspace command',
      tone: 'neutral',
      actions: idleActions(true, legacyConnectorGlanceVisible),
      steps: [
        ...(legacyConnectorGlanceVisible ? legacyConnectorSteps() : []),
        'Left sidebar → pick axon-watch or axon-local.',
        'Right dock → Command tab → try git status or health.',
        'Footer Commands lists every supported command with a Use button.',
        'Hide terminal with the header chip or Ctrl/Cmd+J when you want more mission control space.',
        'Toggle IDE (top-right) for files, editor, terminal, and agent dock (Ctrl/Cmd+\\).',
      ],
    };
  }

  return null;
}
