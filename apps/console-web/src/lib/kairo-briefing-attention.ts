import { personaStatusLabel } from './operator-persona-name';

export type BriefingAttentionSeverity = 'high' | 'warning' | 'info';

export interface KairoBriefingAttention {
  active: boolean;
  severity: BriefingAttentionSeverity;
  message: string;
  badgeCount: number;
}

export function resolveKairoBriefingAttention(input: {
  pendingApprovals: number;
  criticalSignals: number;
  highSignals: number;
  degraded: boolean;
  briefingLoaded: boolean;
}): KairoBriefingAttention {
  if (!input.briefingLoaded) {
    return { active: false, severity: 'info', message: '', badgeCount: 0 };
  }

  if (input.pendingApprovals > 0) {
    const count = input.pendingApprovals;
    return {
      active: true,
      severity: 'high',
      message: `${count} approval${count === 1 ? ' needs' : 's need'} review`,
      badgeCount: count,
    };
  }

  if (input.criticalSignals > 0) {
    const count = input.criticalSignals;
    return {
      active: true,
      severity: 'high',
      message: `${count} critical signal${count === 1 ? '' : 's'}`,
      badgeCount: count,
    };
  }

  if (input.highSignals > 0) {
    const count = input.highSignals;
    return {
      active: true,
      severity: 'warning',
      message: `${count} high-priority signal${count === 1 ? '' : 's'}`,
      badgeCount: count,
    };
  }

  if (input.degraded) {
    return {
      active: true,
      severity: 'warning',
      message: 'Runtime degraded — review briefing',
      badgeCount: 1,
    };
  }

  return { active: false, severity: 'info', message: '', badgeCount: 0 };
}

export function shouldShowBriefingAttentionInCommandMode(
  dockHeroMode: 'command' | 'briefing',
  attention: KairoBriefingAttention,
): boolean {
  return dockHeroMode === 'command' && attention.active;
}

export function briefingAttentionStatusLabel(attention: KairoBriefingAttention): string {
  if (!attention.active) {
    return '';
  }
  return personaStatusLabel(attention.message);
}
