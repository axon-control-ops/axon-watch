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
  r: number;
};

export type GalaxyOrbMeshDot = {
  cx: number;
  cy: number;
  r: number;
  opacity: number;
  accent?: 'cyan' | 'pink';
};

export type GalaxyOrbGlassShard = {
  points: string;
  opacity: number;
  orbitIndex: number;
};

const CENTER = 110;
const TICK_COUNT = 72;

export function galaxyOrbTicks(): GalaxyOrbTick[] {
  return Array.from({ length: TICK_COUNT }, (_, index) => {
    const angle = (index / TICK_COUNT) * Math.PI * 2 - Math.PI / 2;
    const major = index % 8 === 0;
    const outer = 98;
    const inner = major ? 86 : 91;
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
  const radius = 74;
  // Mockup amber cluster near top-left → top arc.
  const angles = [-48, -32, -18, -6, 8].map((degrees) => (degrees * Math.PI) / 180);
  return angles.map((angle, index) => ({
    cx: CENTER + Math.cos(angle) * radius,
    cy: CENTER + Math.sin(angle) * radius,
    r: index === 0 ? 3.1 : 2.4,
  }));
}

/** Dense particle cage for JARVIS mesh depth inside the dial. */
export function galaxyOrbMeshDots(): GalaxyOrbMeshDot[] {
  const dots: GalaxyOrbMeshDot[] = [];
  for (let ring = 0; ring < 6; ring += 1) {
    const count = 12 + ring * 5;
    const radius = 18 + ring * 7;
    for (let i = 0; i < count; i += 1) {
      const angle = (i / count) * Math.PI * 2 + ring * 0.28;
      const jitter = ((i * 17 + ring * 13) % 7) * 0.22;
      const accentPink = (i + ring * 3) % 11 === 0;
      dots.push({
        cx: CENTER + Math.cos(angle) * (radius + jitter),
        cy: CENTER + Math.sin(angle) * (radius + jitter * 0.55),
        r: accentPink ? 1.55 : ring % 2 === 0 ? 1.15 : 0.9,
        opacity: accentPink ? 0.78 : 0.2 + (ring % 3) * 0.11,
        accent: accentPink ? 'pink' : 'cyan',
      });
    }
  }
  return dots;
}

/** Outer glass shard panels orbiting the core (cinematic JARVIS cage). */
export function galaxyOrbGlassShards(): GalaxyOrbGlassShard[] {
  const shards: GalaxyOrbGlassShard[] = [];
  const count = 12;
  const radius = 88;
  for (let i = 0; i < count; i += 1) {
    const angle = (i / count) * Math.PI * 2 - Math.PI / 2;
    const span = 0.22 + (i % 3) * 0.04;
    const inner = radius - 10 - (i % 2) * 3;
    const outer = radius + 4 + (i % 4);
    const a0 = angle - span / 2;
    const a1 = angle + span / 2;
    const p1 = `${CENTER + Math.cos(a0) * inner},${CENTER + Math.sin(a0) * inner}`;
    const p2 = `${CENTER + Math.cos(a0) * outer},${CENTER + Math.sin(a0) * outer}`;
    const p3 = `${CENTER + Math.cos(a1) * outer},${CENTER + Math.sin(a1) * outer}`;
    const p4 = `${CENTER + Math.cos(a1) * inner},${CENTER + Math.sin(a1) * inner}`;
    shards.push({
      points: `${p1} ${p2} ${p3} ${p4}`,
      opacity: 0.18 + (i % 4) * 0.05,
      orbitIndex: i % 3,
    });
  }
  return shards;
}

export function galaxyOrbModeClass(handsFreeEnabled: boolean): string {
  return handsFreeEnabled ? 'kairo-galaxy-orb--hands-free' : 'kairo-galaxy-orb--manual';
}

export function galaxyOrbStatusLabel(
  conversationPhase: GalaxyOrbConversationPhase,
  speaking: boolean,
  capturing = false,
): string {
  if (conversationPhase === 'thinking') {
    return 'BUSY';
  }
  if (speaking || conversationPhase === 'speaking') {
    return 'SPEAKING';
  }
  // Only claim LISTENING when the mic session is actually open.
  if (capturing || conversationPhase === 'listening') {
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
    return 'Hands-free';
  }
  return 'Manual';
}

export function galaxyOrbStateClass(
  state: KairoPresenceState,
  speaking: boolean,
  conversationPhase: GalaxyOrbConversationPhase = 'idle',
  capturing = false,
  agentStreamActive = false,
): string {
  if (agentStreamActive) {
    return 'kairo-galaxy-orb--thinking kairo-galaxy-orb--busy kairo-galaxy-orb--autonomous';
  }
  if (conversationPhase === 'thinking') {
    return 'kairo-galaxy-orb--thinking kairo-galaxy-orb--busy';
  }
  if (speaking || conversationPhase === 'speaking') {
    return 'kairo-galaxy-orb--speaking';
  }
  if (capturing || conversationPhase === 'listening') {
    return 'kairo-galaxy-orb--listening';
  }
  if (state === 'alerting') {
    return 'kairo-galaxy-orb--alerting';
  }
  if (state === 'privacy_blocked') {
    return 'kairo-galaxy-orb--muted';
  }
  // "observing" means watch is connected — not that the mic is open.
  if (state === 'observing') {
    return 'kairo-galaxy-orb--standby kairo-galaxy-orb--observing';
  }
  if (state === 'listening') {
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
  gateFeedback: string | null = null,
): string {
  if (gateFeedback) {
    return gateFeedback;
  }
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
    return `Say "${OPERATOR_PERSONA_NAME}" for commands · Space hold-to-talk`;
  }
  if (conversationPhase === 'listening') {
    return 'Listening — release to send';
  }
  if (state === 'alerting') {
    return 'Tap for hands-free · hold to talk · long-press to move';
  }
  return 'Tap for hands-free · hold to talk · say "change brain to …" to switch models';
}
