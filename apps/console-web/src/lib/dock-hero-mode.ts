export type DockHeroMode = 'command' | 'briefing';

export function resolveDefaultDockHeroMode(input: {
  pendingApprovals: number;
  criticalSignals: number;
  highSignals: number;
}): DockHeroMode {
  if (input.pendingApprovals > 0) {
    return 'briefing';
  }

  if (input.criticalSignals > 0 || input.highSignals > 0) {
    return 'briefing';
  }

  return 'command';
}

export function dockHeroModeLabel(mode: DockHeroMode): string {
  return mode === 'command' ? 'Command' : 'KAIRO Briefing';
}

export function dockHeroModeTitle(mode: DockHeroMode): string {
  return dockHeroModeLabel(mode);
}
