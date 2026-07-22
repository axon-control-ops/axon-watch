import type { BrainGraphNode, BrainNodeKind, BrainNodeTone } from '../../lib/operator-brain-graph-view';

export type GalaxyNodeColors = {
  base: number;
  emissive: number;
  emissiveIntensity: number;
};

const KIND_BASE: Record<BrainNodeKind | string, number> = {
  core: 0x7aebff,
  workspace: 0xb8ecff,
  run: 0x6b8fa8,
  signal: 0xff6aa8,
  connector: 0x5a9fff,
  mailbox: 0x7ee0a8,
};

const TONE_EMISSIVE: Record<BrainNodeTone | string, number> = {
  nominal: 0x7ad8ff,
  attention: 0xffa040,
  critical: 0xff5050,
};

const TONE_INTENSITY: Record<BrainNodeTone | string, number> = {
  nominal: 0.85,
  attention: 1.05,
  critical: 1.25,
};

export function galaxyNodeColors(node: BrainGraphNode): GalaxyNodeColors {
  if (node.kind === 'workspace' && node.tone === 'nominal') {
    // Bright cyan-white orbs — matches the older “nebula cluster” look.
    return { base: 0xd7f6ff, emissive: 0xa8eaff, emissiveIntensity: 1.15 };
  }
  if (node.kind === 'signal') {
    return { base: 0xff7eb6, emissive: 0xff4d8d, emissiveIntensity: 1.35 };
  }
  if (node.kind === 'connector') {
    return { base: 0x7ab6ff, emissive: 0x4d8cff, emissiveIntensity: 1.2 };
  }
  const base = KIND_BASE[node.kind] ?? 0x6688aa;
  const emissive = TONE_EMISSIVE[node.tone] ?? TONE_EMISSIVE.nominal;
  const emissiveIntensity =
    node.kind === 'core'
      ? 1.85
      : (TONE_INTENSITY[node.tone] ?? TONE_INTENSITY.nominal);

  return { base, emissive, emissiveIntensity };
}

export function galaxyEdgeColor(kind: string): number {
  if (kind === 'emits') {
    return 0xffa040;
  }
  if (kind === 'executes') {
    return 0x48c4ff;
  }
  return 0x3a6a88;
}

export const GALAXY_BACKGROUND = 0x040810;
export const GALAXY_FOG = 0x040810;
export const GALAXY_STAR_COLOR = 0x88ccff;
