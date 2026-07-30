import type { CompanyRosterAlertBadgeTone } from '../features/workspace-agents/company-roster-failure-view';
import { operatorFailureRetryLabel } from './operator-failure-copy';

import { buildConnectorIdeQuickGuide } from './ide-quick-guide-connectors';
import { ideSidebarStubActionAriaLabel } from './ide-sidebar-stub-view';

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
  | 'open-team'
  | 'open-source-control'
  | 'open-search'
  | 'retry-employee-shift';

export type IdeQuickGuideAction = {
  id: IdeQuickGuideActionId;
  label: string;
};

/** Whether a quick-guide CTA uses the emphasized secondary styling when paired with expand. */
export function ideQuickGuideActionIsSecondary(
  actionId: IdeQuickGuideActionId,
  actions: IdeQuickGuideAction[],
): boolean {
  const ids = new Set(actions.map((action) => action.id));

  if (actionId === 'retry-employee-shift' && ids.has('expand-agent-dock')) {
    return true;
  }

  return false;
}

/** Descriptive label for quick-guide CTA buttons (visible text stays short). */
export function ideQuickGuideActionAriaLabel(action: IdeQuickGuideAction): string {
  if (action.id === 'open-connectors') {
    return 'Open connectors in Mission Control';
  }

  if (action.id === 'open-team') {
    return 'Open Team sidebar in the left activity bar';
  }

  if (action.id === 'open-source-control') {
    return 'Open Source Control sidebar in the left activity bar';
  }

  if (action.id === 'open-search') {
    return 'Open Search sidebar in the left activity bar';
  }

  if (action.id === 'expand-agent-dock') {
    return ideSidebarStubActionAriaLabel('Expand agent dock', 'agent');
  }

  if (action.id === 'show-terminal') {
    return ideSidebarStubActionAriaLabel('Show terminal', 'terminal');
  }

  if (action.id === 'retry-employee-shift') {
    return ideSidebarStubActionAriaLabel(action.label, 'agent');
  }

  return action.label;
}

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
  return interrupted
    ? 'Open Team and tap Continue on their roster card to pick up where they left off.'
    : 'Open Team and tap Try again on their roster card, or talk it through.';
}

function employeeFailureComposerBannerStep(interrupted: boolean): string {
  return interrupted
    ? 'Open Team and tap Continue on their roster card to pick up where they left off.'
    : 'Open Team and tap Try again on their roster card, or talk it through.';
}

function rosterFailureQuickGuideTone(
  tone: CompanyRosterAlertBadgeTone | null | undefined,
): IdeQuickGuideTone {
  return tone === 'interrupted' ? 'interrupted' : 'failure';
}

function rosterFailureQuickGuideTitle(
  count: number,
  tone: CompanyRosterAlertBadgeTone | null | undefined,
): string {
  if (count === 1) {
    return tone === 'interrupted'
      ? "Teammate's job was interrupted — open Team to continue"
      : "Teammate's last job failed — open Team to review";
  }

  if (tone === 'interrupted') {
    return `${count} interrupted jobs — open Team to continue`;
  }

  return `${count} teammates need attention — open Team to review`;
}

function rosterFailureQuickGuideFallbackStep(
  count: number,
  tone: CompanyRosterAlertBadgeTone | null | undefined,
): string {
  if (count === 1) {
    return tone === 'interrupted'
      ? 'A teammate has an interrupted job that can be continued.'
      : 'A teammate needs attention after a failed job.';
  }

  if (tone === 'interrupted') {
    return `${count} teammates have interrupted jobs that can be continued.`;
  }

  if (tone === 'mixed') {
    return `${count} teammates need attention after failed or interrupted jobs.`;
  }

  return `${count} teammates need attention after failed jobs.`;
}

function rosterFailureRecoveryStep(
  tone: CompanyRosterAlertBadgeTone | null | undefined,
): string {
  if (tone === 'interrupted') {
    return `Team in the left activity bar shows who was interrupted and offers ${operatorFailureRetryLabel(true)}.`;
  }

  if (tone === 'mixed') {
    return (
      'Team in the left activity bar shows who needs attention and offers '
      + `${operatorFailureRetryLabel(true)} or ${operatorFailureRetryLabel(false)}.`
    );
  }

  return `Team in the left activity bar shows who failed and offers ${operatorFailureRetryLabel(false)}.`;
}

function buildRosterFailureQuickGuide(input: {
  failedEmployeeCount?: number;
  failedEmployeesHint?: string | null;
  rosterAlertTone?: CompanyRosterAlertBadgeTone | null;
  terminalVisible: boolean;
  teamExpanded?: boolean;
}): IdeQuickGuide | null {
  const count = input.failedEmployeeCount ?? 0;
  if (count <= 0) {
    return null;
  }
  // Team already owns the failure surface — don't also sticky-banner "Open Team".
  if (input.teamExpanded) {
    return null;
  }

  const tone = input.rosterAlertTone ?? 'failure';
  const hint = (input.failedEmployeesHint ?? '').trim();
  const actions: IdeQuickGuideAction[] = [{ id: 'open-team', label: 'Open Team' }];
  if (!input.terminalVisible) {
    actions.push({ id: 'show-terminal', label: 'Show terminal' });
  }

  return {
    title: rosterFailureQuickGuideTitle(count, tone),
    tone: rosterFailureQuickGuideTone(tone),
    actions,
    steps: [
      hint || rosterFailureQuickGuideFallbackStep(count, tone),
      rosterFailureRecoveryStep(tone),
      ...(input.terminalVisible
        ? []
        : ['Ctrl/Cmd+J opens the terminal when you need shell output.']),
    ],
  };
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
  /** Continue / Try again — omitted when no active teammate record. */
  employeeRetryActionLabel?: string | null;
  requiredConnectorsUnavailable?: number;
  legacyConnectorGlanceVisible?: boolean;
  watchConnected?: boolean;
  failedEmployeeCount?: number;
  failedEmployeesHint?: string | null;
  rosterAlertTone?: CompanyRosterAlertBadgeTone | null;
  dirtyFileCount?: number;
  sourceControlExpanded?: boolean;
  workspaceFilesLoadState?: 'idle' | 'loading' | 'loaded' | 'error';
  searchExpanded?: boolean;
  /** Team activity view already open — skip redundant "Open Team" failure sticky. */
  teamExpanded?: boolean;
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
      title: interrupted
        ? 'Job interrupted — expand the agent dock to continue'
        : 'Last job failed — expand the agent dock to retry',
      tone: interrupted ? 'interrupted' : 'failure',
      actions: [
        { id: 'expand-agent-dock', label: 'Expand agent dock' },
        ...(retryLabel ? [{ id: 'retry-employee-shift' as const, label: retryLabel }] : []),
      ],
      steps: withEmployeeFailureDetail(input.employeeFailureLine, [
        'Ctrl/Cmd+\\ toggles the agent dock.',
        employeeFailureBannerStep(interrupted),
        'Click AGENT in the editor status bar or the right-edge reopen strip.',
      ]),
    };
  }

  if (
    !input.agentDockCollapsed &&
    (input.employeeFailureLine ?? '').trim() &&
    idleRun &&
    !input.streaming &&
    input.pendingApprovals <= 0
  ) {
    // Dock banner owns the failure line; retry lives on Team roster (not composer).
    if (input.teamExpanded) {
      return null;
    }
    const interrupted = Boolean(input.employeeShiftInterrupted);
    const actions: IdeQuickGuideAction[] = [{ id: 'open-team', label: 'Open Team' }];
    if (!input.terminalVisible) {
      actions.push({ id: 'show-terminal', label: 'Show terminal' });
    }

    return {
      title: interrupted
        ? 'Job interrupted — continue from Team'
        : 'Last job failed — retry from Team',
      tone: interrupted ? 'interrupted' : 'failure',
      actions,
      steps: [
        employeeFailureComposerBannerStep(interrupted),
        'The composer banner explains the failure; retry stays on the Team roster.',
        ...(input.terminalVisible
          ? []
          : ['Ctrl/Cmd+J opens the terminal when you need shell output.']),
      ],
    };
  }

  const connectorGuide = buildConnectorIdeQuickGuide({
    idleRun,
    terminalVisible: input.terminalVisible,
    watchConnected,
    requiredConnectorsUnavailable,
    legacyConnectorGlanceVisible,
  });
  if (connectorGuide) {
    return connectorGuide;
  }

  if (idleRun && !(input.employeeFailureLine ?? '').trim()) {
    const rosterGuide = buildRosterFailureQuickGuide(input);
    if (rosterGuide) {
      return rosterGuide;
    }
  }

  const dirtyFileCount = input.dirtyFileCount ?? 0;
  if (idleRun && dirtyFileCount > 0 && !input.sourceControlExpanded) {
    return {
      title:
        dirtyFileCount === 1
          ? 'Unsaved changes — open Source Control to review'
          : `${dirtyFileCount} unsaved files — open Source Control to review`,
      tone: 'attention',
      actions: [{ id: 'open-source-control', label: 'Open Source Control' }],
      steps: [
        dirtyFileCount === 1
          ? 'One workspace file tab has edits that are not saved yet.'
          : `${dirtyFileCount} workspace file tabs have edits that are not saved yet.`,
        'Source Control in the left activity bar lists each unsaved file — click to jump back.',
        'Ctrl/Cmd+Shift+G opens Source Control from anywhere in the IDE.',
        'Activity bar badge · status bar Unsaved chip and pill · dirty dot on editor tabs · save from the editor when ready.',
      ],
    };
  }

  if (
    idleRun &&
    input.workspaceFilesLoadState === 'error' &&
    (input.watchConnected ?? true) &&
    !input.searchExpanded
  ) {
    return {
      title: 'Workspace files failed to load — open Search to retry',
      tone: 'attention',
      actions: [{ id: 'open-search', label: 'Open Search' }],
      steps: [
        'Could not load workspace files — use Retry in the Search sidebar, or check the watch connection.',
        'Ctrl/Cmd+Shift+F opens Search from anywhere in the IDE.',
        'Activity bar warning pulse · editor status bar SEARCH ERR chip · Search panel retry button.',
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
        title: 'Terminal hidden — shell output is in the bottom panel',
        tone: 'attention',
        actions: [{ id: 'show-terminal', label: 'Show terminal' }],
        steps: [
          'This tip opens the workbench terminal (not the top ATTENTION chip — that is for signals).',
          'Ctrl/Cmd+J toggles the terminal panel.',
          'Editor status bar TERMINAL chip and the left activity bar also reopen it.',
        ],
      };
    }

    if (input.runPhase === 'review_ready') {
      return {
        title: 'Terminal hidden — review command output below',
        tone: 'attention',
        actions: [{ id: 'show-terminal', label: 'Show terminal' }],
        steps: [
          'This tip opens the workbench terminal (not the top ATTENTION chip — that is for signals).',
          'Ctrl/Cmd+J toggles the terminal panel.',
          'Complete the run from the agent dock when ready.',
        ],
      };
    }

    // Idle + dock open + terminal closed: status-bar chip is enough — no banner.
    return null;
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
        'Ctrl/Cmd+Shift+F — Search sidebar (filter workspace file paths)',
        'Ctrl/Cmd+Shift+G — Source Control sidebar',
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

  if (!(input.employeeFailureLine ?? '').trim()) {
    const rosterGuide = buildRosterFailureQuickGuide(input);
    if (rosterGuide) {
      return rosterGuide;
    }
  }

  return null;
}
