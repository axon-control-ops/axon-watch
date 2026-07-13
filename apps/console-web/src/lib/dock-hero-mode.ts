import { OPERATOR_PERSONA_NAME } from './operator-persona-name';

export type DockHeroMode = 'command' | 'briefing';

export function resolveDefaultDockHeroMode(input: {
  pendingApprovals: number;
  criticalSignals: number;
  highSignals: number;
  nextSafeActions?: number;
  actionableInboxCount?: number;
}): DockHeroMode {
  if (input.pendingApprovals > 0) {
    return 'briefing';
  }

  if (input.criticalSignals > 0 || input.highSignals > 0) {
    return 'briefing';
  }

  if ((input.nextSafeActions ?? 0) > 0 || (input.actionableInboxCount ?? 0) > 0) {
    return 'briefing';
  }

  return 'command';
}

export function dockHeroModeLabel(mode: DockHeroMode): string {
  return mode === 'command' ? 'Command' : `${OPERATOR_PERSONA_NAME} Briefing`;
}

export function dockHeroModeTitle(mode: DockHeroMode): string {
  return dockHeroModeLabel(mode);
}
