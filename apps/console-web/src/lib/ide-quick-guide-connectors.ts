import type { IdeQuickGuide, IdeQuickGuideAction } from './ide-quick-guide';

/** Connector/watch-lane quick-guide cards when idle and no higher-priority nudge applies. */
export function buildConnectorIdeQuickGuide(input: {
  idleRun: boolean;
  terminalVisible: boolean;
  watchConnected: boolean;
  requiredConnectorsUnavailable: number;
  legacyConnectorGlanceVisible: boolean;
}): IdeQuickGuide | null {
  if (!input.idleRun) {
    return null;
  }

  if (!input.watchConnected) {
    const actions: IdeQuickGuideAction[] = [{ id: 'open-connectors', label: 'Open connectors' }];
    if (!input.terminalVisible) {
      actions.push({ id: 'show-terminal', label: 'Show terminal' });
    }

    return {
      title: 'Watch offline — connector probes paused',
      tone: 'attention',
      actions,
      steps: [
        'Watch offline — connector probes paused until the watch reconnects.',
        'Mission Control → Connectors shows live status once the stack is back up.',
        'Editor status bar WATCH OFFLINE chip · footer chip · Run activity pulse.',
        ...(input.terminalVisible
          ? []
          : ['Ctrl/Cmd+J opens the terminal when you need shell output in the workbench.']),
      ],
    };
  }

  if (input.requiredConnectorsUnavailable > 0) {
    const count = input.requiredConnectorsUnavailable;
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

  if (input.legacyConnectorGlanceVisible) {
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

  return null;
}
