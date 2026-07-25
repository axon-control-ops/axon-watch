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
const TICK_COUNT = 96;

export type GalaxyOrbRingSpec = {
  r: number;
  kind: 'solid' | 'dashed' | 'fine' | 'heavy';
  opacity: number;
};

export type GalaxyOrbGearSeg = {
  d: string;
  opacity: number;
};

export type GalaxyOrbSpark = {
  cx: number;
  cy: number;
  r: number;
  tone: 'amber' | 'cyan';
};

export type GalaxyOrbFreqTick = {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  major: boolean;
};

export function galaxyOrbTicks(): GalaxyOrbTick[] {
  return Array.from({ length: TICK_COUNT }, (_, index) => {
    const angle = (index / TICK_COUNT) * Math.PI * 2 - Math.PI / 2;
    const major = index % 6 === 0;
    const outer = 102;
    const inner = major ? 88 : 94;
    return {
      x1: CENTER + Math.cos(angle) * outer,
      y1: CENTER + Math.sin(angle) * outer,
      x2: CENTER + Math.cos(angle) * inner,
      y2: CENTER + Math.sin(angle) * inner,
      major,
    };
  });
}

/** Dense frequency meter around the plasma core (JARVIS-style). */
export function galaxyOrbFreqTicks(): GalaxyOrbFreqTick[] {
  const count = 64;
  return Array.from({ length: count }, (_, index) => {
    const angle = (index / count) * Math.PI * 2 - Math.PI / 2;
    const major = index % 4 === 0;
    const outer = 48;
    const inner = major ? 36 : 41;
    return {
      x1: CENTER + Math.cos(angle) * outer,
      y1: CENTER + Math.sin(angle) * outer,
      x2: CENTER + Math.cos(angle) * inner,
      y2: CENTER + Math.sin(angle) * inner,
      major,
    };
  });
}

export function galaxyOrbConcentricRings(): GalaxyOrbRingSpec[] {
  return [
    { r: 104, kind: 'fine', opacity: 0.28 },
    { r: 97, kind: 'dashed', opacity: 0.55 },
    { r: 90, kind: 'solid', opacity: 0.5 },
    { r: 83, kind: 'dashed', opacity: 0.62 },
    { r: 76, kind: 'heavy', opacity: 0.45 },
    { r: 69, kind: 'fine', opacity: 0.4 },
    { r: 62, kind: 'dashed', opacity: 0.58 },
    { r: 55, kind: 'solid', opacity: 0.48 },
    { r: 50, kind: 'fine', opacity: 0.55 },
  ];
}

/** Armor / gear notches on mid rings. */
export function galaxyOrbGearSegments(): GalaxyOrbGearSeg[] {
  const segs: GalaxyOrbGearSeg[] = [];
  const radius = 76;
  const count = 18;
  for (let i = 0; i < count; i += 1) {
    if (i % 3 === 0) continue;
    const angle = (i / count) * Math.PI * 2 - Math.PI / 2;
    const span = 0.11;
    const a0 = angle - span / 2;
    const a1 = angle + span / 2;
    const inner = radius - 3.5;
    const outer = radius + 5.5;
    const p = (a: number, r: number) =>
      `${CENTER + Math.cos(a) * r},${CENTER + Math.sin(a) * r}`;
    segs.push({
      d: `M ${p(a0, inner)} L ${p(a0, outer)} L ${p(a1, outer)} L ${p(a1, inner)} Z`,
      opacity: 0.35 + (i % 4) * 0.08,
    });
  }
  return segs;
}

export function galaxyOrbSparks(): GalaxyOrbSpark[] {
  const sparks: GalaxyOrbSpark[] = [];
  for (let i = 0; i < 22; i += 1) {
    const angle = (i / 22) * Math.PI * 2 + i * 0.17;
    const radius = 92 + (i % 5) * 3.2;
    sparks.push({
      cx: CENTER + Math.cos(angle) * radius,
      cy: CENTER + Math.sin(angle) * radius,
      r: i % 3 === 0 ? 1.8 : 1.15,
      tone: i % 4 === 0 ? 'amber' : 'cyan',
    });
  }
  return sparks;
}

export function galaxyOrbBeads(): GalaxyOrbBead[] {
  const radius = 74;
  // Mockup amber cluster near top-left → top arc.
  const angles = [-48, -32, -18, -6, 8, 22, 38].map((degrees) => (degrees * Math.PI) / 180);
  return angles.map((angle, index) => ({
    cx: CENTER + Math.cos(angle) * radius,
    cy: CENTER + Math.sin(angle) * radius,
    r: index === 0 ? 3.1 : 2.2,
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
  captureMode: 'manual' | 'hands_free' | 'barge_in' = 'manual',
): string {
  if (conversationPhase === 'thinking') {
    return 'BUSY';
  }
  if (speaking || conversationPhase === 'speaking') {
    return 'SPEAKING';
  }
  // Ambient hands-free capture restarts every Chromium no-speech cycle — do not
  // claim LISTENING for that. Manual PTT owns the label.
  const operatorOwnedListen =
    conversationPhase === 'listening' || (capturing && captureMode === 'manual');
  if (operatorOwnedListen) {
    return 'LISTENING';
  }
  return 'READY';
}

export function galaxyOrbModeLabel(
  handsFreeEnabled: boolean,
  conversationPhase: GalaxyOrbConversationPhase,
  handsFreeArmed = handsFreeEnabled,
): string {
  if (conversationPhase === 'thinking') {
    return 'Checking…';
  }
  if (conversationPhase === 'speaking') {
    return 'Voice live';
  }
  if (handsFreeArmed) {
    return 'Hands-free';
  }
  if (handsFreeEnabled) {
    return 'Unlock voice';
  }
  return 'Manual';
}

export function galaxyOrbTriggerAriaLabel(
  personaName: string,
  voiceBlocked: boolean,
  handsFreeEnabled: boolean,
): string {
  if (voiceBlocked) {
    return `${personaName} voice muted`;
  }
  if (handsFreeEnabled) {
    return `${personaName} hands-free — tap for command ring, hold to talk, long-press to move`;
  }
  return `${personaName} manual — tap for command ring, hold to talk, long-press to move`;
}

export function galaxyOrbStateClass(
  state: KairoPresenceState,
  speaking: boolean,
  conversationPhase: GalaxyOrbConversationPhase = 'idle',
  capturing = false,
  agentStreamActive = false,
  captureMode: 'manual' | 'hands_free' | 'barge_in' = 'manual',
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
  const operatorOwnedListen =
    conversationPhase === 'listening' || (capturing && captureMode === 'manual');
  if (operatorOwnedListen) {
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
    return 'Tap for command ring · hold to talk · long-press to move';
  }
  return 'Tap for command ring · hold to talk · say "change brain to …" to switch models';
}
