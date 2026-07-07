import type { KairoPresenceState } from '../../lib/kairo-presence';

export type GalaxyOrbTick = {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  major: boolean;
};

export type GalaxyOrbBead = {
  cx: number;
  cy: number;
};

const CENTER = 100;
const TICK_COUNT = 48;

export function galaxyOrbTicks(): GalaxyOrbTick[] {
  return Array.from({ length: TICK_COUNT }, (_, index) => {
    const angle = (index / TICK_COUNT) * Math.PI * 2 - Math.PI / 2;
    const major = index % 6 === 0;
    const outer = 88;
    const inner = major ? 76 : 81;
    return {
      x1: CENTER + Math.cos(angle) * outer,
      y1: CENTER + Math.sin(angle) * outer,
      x2: CENTER + Math.cos(angle) * inner,
      y2: CENTER + Math.sin(angle) * inner,
      major,
    };
  });
}

export function galaxyOrbBeads(): GalaxyOrbBead[] {
  const radius = 72;
  const angles = [-24, -12, 0, 12, 24].map((degrees) => (degrees * Math.PI) / 180);
  return angles.map((angle) => ({
    cx: CENTER + Math.cos(angle) * radius,
    cy: CENTER + Math.sin(angle) * radius,
  }));
}

export function galaxyOrbStateClass(
  state: KairoPresenceState,
  speaking: boolean,
  conversationPhase: 'idle' | 'listening' | 'thinking' | 'speaking' = 'idle',
): string {
  if (speaking || conversationPhase === 'speaking') {
    return 'kairo-galaxy-orb--speaking';
  }
  if (conversationPhase === 'thinking') {
    return 'kairo-galaxy-orb--thinking';
  }
  if (conversationPhase === 'listening') {
    return 'kairo-galaxy-orb--listening';
  }
  if (state === 'alerting') {
    return 'kairo-galaxy-orb--alerting';
  }
  if (state === 'privacy_blocked') {
    return 'kairo-galaxy-orb--muted';
  }
  if (state === 'observing' || state === 'listening') {
    return 'kairo-galaxy-orb--listening';
  }
  return 'kairo-galaxy-orb--standby';
}

export function galaxyOrbModelLabel(modelId: string | null | undefined): string {
  if (!modelId) {
    return 'AUTO';
  }
  const normalized = modelId.replace(/^models\//, '').replace(/\s+/g, '-').toUpperCase();
  if (normalized.length <= 14) {
    return normalized;
  }
  return `${normalized.slice(0, 11)}…`;
}

export function galaxyOrbHint(
  state: KairoPresenceState,
  speaking: boolean,
  conversationPhase: 'idle' | 'listening' | 'thinking' | 'speaking' = 'idle',
): string {
  if (conversationPhase === 'thinking') {
    return 'Working through your request';
  }
  if (conversationPhase === 'listening') {
    return 'Listening — ask or dispatch below';
  }
  if (speaking || conversationPhase === 'speaking') {
    return 'Briefing in progress';
  }
  if (state === 'privacy_blocked') {
    return 'Voice muted in privacy mode';
  }
  if (state === 'alerting') {
    return 'Attention needed — tap orb for briefing';
  }
  return 'Tap orb to speak briefing · hold orb or Space to talk';
}
