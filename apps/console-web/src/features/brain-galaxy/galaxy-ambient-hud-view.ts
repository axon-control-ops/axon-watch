/**
 * Ambient holographic HUD windows for Brain Galaxy — continuous JARVIS-like activity.
 */

export type GalaxyAmbientPanelKind =
  | 'watch'
  | 'signal'
  | 'run'
  | 'route'
  | 'presence'
  | 'scan';

export type GalaxyAmbientPanel = {
  id: string;
  kind: GalaxyAmbientPanelKind;
  title: string;
  body: string;
  tone: 'nominal' | 'attention' | 'critical' | 'info';
};

export type GalaxyAmbientHudInput = {
  nowMs: number;
  presencePhase: string;
  workspaceLabel: string | null;
  criticalSignals: number;
  highSignals: number;
  runPhaseLabel: string | null;
  topSignalTitle: string | null;
  specialtyRouteLine: string | null;
  watchConnected: boolean;
};

const ROTATE_MS = 4200;
const VISIBLE = 3;

export function buildGalaxyAmbientPanels(input: GalaxyAmbientHudInput): GalaxyAmbientPanel[] {
  const workspace = input.workspaceLabel?.trim() || 'operator fabric';
  const panels: GalaxyAmbientPanel[] = [
    {
      id: 'presence',
      kind: 'presence',
      title: 'VAXON CORE',
      body: presenceLine(input.presencePhase),
      tone: input.presencePhase === 'alerting' ? 'critical' : 'info',
    },
    {
      id: 'watch',
      kind: 'watch',
      title: 'WATCH LINK',
      body: input.watchConnected
        ? `Fabric linked · monitoring ${workspace}`
        : 'Watch fabric reconnecting…',
      tone: input.watchConnected ? 'nominal' : 'attention',
    },
    {
      id: 'scan',
      kind: 'scan',
      title: 'CONTINUOUS SCAN',
      body: `Sweeping ${workspace} · nodes + signals + runs`,
      tone: 'info',
    },
  ];

  if (input.topSignalTitle) {
    panels.push({
      id: 'signal',
      kind: 'signal',
      title: input.criticalSignals > 0 ? 'CRITICAL SIGNAL' : 'ACTIVE SIGNAL',
      body: input.topSignalTitle,
      tone: input.criticalSignals > 0 ? 'critical' : 'attention',
    });
  } else if (input.criticalSignals + input.highSignals > 0) {
    panels.push({
      id: 'signal',
      kind: 'signal',
      title: 'ATTENTION STACK',
      body: `${input.criticalSignals} critical · ${input.highSignals} high`,
      tone: input.criticalSignals > 0 ? 'critical' : 'attention',
    });
  }

  if (input.runPhaseLabel) {
    panels.push({
      id: 'run',
      kind: 'run',
      title: 'ACTIVE RUN',
      body: `Phase ${input.runPhaseLabel} · ${workspace}`,
      tone: 'info',
    });
  }

  if (input.specialtyRouteLine) {
    panels.push({
      id: 'route',
      kind: 'route',
      title: 'SPECIALTY ROUTE',
      body: input.specialtyRouteLine,
      tone: 'nominal',
    });
  }

  return panels;
}

export function selectVisibleAmbientPanels(
  panels: readonly GalaxyAmbientPanel[],
  nowMs: number,
  rotateMs = ROTATE_MS,
  visible = VISIBLE,
): GalaxyAmbientPanel[] {
  if (panels.length === 0) {
    return [];
  }
  const count = Math.min(visible, panels.length);
  if (panels.length <= count) {
    return [...panels];
  }
  const offset = Math.floor(nowMs / rotateMs) % panels.length;
  const selected: GalaxyAmbientPanel[] = [];
  for (let index = 0; index < count; index += 1) {
    selected.push(panels[(offset + index) % panels.length]!);
  }
  return selected;
}

export function galaxyAmbientSpokenLine(input: GalaxyAmbientHudInput): string {
  if (input.specialtyRouteLine) {
    return input.specialtyRouteLine;
  }
  if (input.topSignalTitle && input.criticalSignals > 0) {
    return `I am watching ${input.topSignalTitle}.`;
  }
  if (input.runPhaseLabel) {
    return `Run is in ${input.runPhaseLabel}. Standing by.`;
  }
  return presenceLine(input.presencePhase);
}

function presenceLine(phase: string): string {
  switch (phase) {
    case 'listening':
      return 'Listening — speak when ready.';
    case 'thinking':
      return 'Working the problem…';
    case 'speaking':
      return 'Speaking now.';
    case 'autonomous':
      return 'Agent stream live — I am in the loop.';
    case 'alerting':
      return 'Attention — critical path is hot.';
    case 'workspace_selected':
      return 'Workspace locked. Ready to dispatch.';
    default:
      return 'Online. Continuous watch engaged.';
  }
}
