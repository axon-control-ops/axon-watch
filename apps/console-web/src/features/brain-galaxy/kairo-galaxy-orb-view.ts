import type { KairoPresenceState } from '../../lib/kairo-presence';
import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';

export type GalaxyOrbConversationPhase = 'idle' | 'listening' | 'thinking' | 'speaking';

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

export function galaxyOrbModeClass(handsFreeEnabled: boolean): string {
  return handsFreeEnabled ? 'kairo-galaxy-orb--hands-free' : 'kairo-galaxy-orb--manual';
}

export function galaxyOrbStatusLabel(
  conversationPhase: GalaxyOrbConversationPhase,
  speaking: boolean,
): string {
  if (conversationPhase === 'thinking') {
    return 'BUSY';
  }
  if (speaking || conversationPhase === 'speaking') {
    return 'SPEAKING';
  }
  if (conversationPhase === 'listening') {
    return 'LISTENING';
  }
  return 'READY';
}

export function galaxyOrbModeLabel(
  handsFreeEnabled: boolean,
  conversationPhase: GalaxyOrbConversationPhase,
): string {
  if (conversationPhase === 'thinking') {
    return 'Checking…';
  }
  if (conversationPhase === 'speaking') {
    return 'Voice live';
  }
  if (handsFreeEnabled) {
    return '';
  }
  return 'Manual';
}

export function galaxyOrbStateClass(
  state: KairoPresenceState,
  speaking: boolean,
  conversationPhase: GalaxyOrbConversationPhase = 'idle',
): string {
  if (conversationPhase === 'thinking') {
    return 'kairo-galaxy-orb--thinking kairo-galaxy-orb--busy';
  }
  if (speaking || conversationPhase === 'speaking') {
    return 'kairo-galaxy-orb--speaking';
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
  conversationPhase: GalaxyOrbConversationPhase = 'idle',
  handsFreeEnabled = false,
): string {
  if (conversationPhase === 'thinking') {
    return `${OPERATOR_PERSONA_NAME} is checking — hold on or tap Interrupt`;
  }
  if (speaking || conversationPhase === 'speaking') {
    return `${OPERATOR_PERSONA_NAME} speaking — say "stop" or "${OPERATOR_PERSONA_NAME} …" to barge in`;
  }
  if (state === 'privacy_blocked') {
    return 'Voice muted in privacy mode';
  }
  if (handsFreeEnabled) {
    return `Say "${OPERATOR_PERSONA_NAME}" for commands`;
  }
  if (conversationPhase === 'listening') {
    return 'Listening — release to send';
  }
  if (state === 'alerting') {
    return 'Tap orb for hands-free · hold orb to talk';
  }
  return 'Tap orb for hands-free · hold orb or use Mic to talk';
}
