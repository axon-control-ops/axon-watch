import type { BrainGraphNode, BrainNodeKind, BrainNodeTone } from '../../lib/operator-brain-graph-view';

export type GalaxyNodeColors = {
  base: number;
  emissive: number;
  emissiveIntensity: number;
};

const KIND_BASE: Record<BrainNodeKind | string, number> = {
  core: 0x48c4ff,
  workspace: 0x3a9fd4,
  run: 0x6b8fa8,
  signal: 0xffa040,
  connector: 0x5a8cff,
};

const TONE_EMISSIVE: Record<BrainNodeTone | string, number> = {
  nominal: 0x224466,
  attention: 0xffa040,
  critical: 0xff5050,
};

const TONE_INTENSITY: Record<BrainNodeTone | string, number> = {
  nominal: 0.35,
  attention: 0.75,
  critical: 1.1,
};

export function galaxyNodeColors(node: BrainGraphNode): GalaxyNodeColors {
  const base = KIND_BASE[node.kind] ?? 0x6688aa;
  const emissive = TONE_EMISSIVE[node.tone] ?? TONE_EMISSIVE.nominal;
  const emissiveIntensity =
    node.kind === 'core'
      ? 1.4
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
