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

/** Stable 0–360 hue from workspace id — muted family for easy spotting. */
export function workspaceHueFromId(workspaceId: string): number {
  const raw = workspaceId.trim() || 'workspace';
  let hash = 2166136261;
  for (let i = 0; i < raw.length; i += 1) {
    hash ^= raw.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return Math.abs(hash) % 360;
}

function hslToHex(h: number, s: number, l: number): number {
  const sat = Math.max(0, Math.min(1, s));
  const light = Math.max(0, Math.min(1, l));
  const chroma = (1 - Math.abs(2 * light - 1)) * sat;
  const hp = (((h % 360) + 360) % 360) / 60;
  const x = chroma * (1 - Math.abs((hp % 2) - 1));
  let r = 0;
  let g = 0;
  let b = 0;
  if (hp >= 0 && hp < 1) {
    r = chroma;
    g = x;
  } else if (hp < 2) {
    r = x;
    g = chroma;
  } else if (hp < 3) {
    g = chroma;
    b = x;
  } else if (hp < 4) {
    g = x;
    b = chroma;
  } else if (hp < 5) {
    r = x;
    b = chroma;
  } else {
    r = chroma;
    b = x;
  }
  const m = light - chroma / 2;
  const toByte = (channel: number) => Math.round(Math.max(0, Math.min(1, channel + m)) * 255);
  return (toByte(r) << 16) | (toByte(g) << 8) | toByte(b);
}

export function galaxyNodeColors(node: BrainGraphNode): GalaxyNodeColors {
  if (node.kind === 'workspace' && node.tone === 'nominal') {
    const hue = workspaceHueFromId(node.workspace_id || node.node_id);
    return {
      base: hslToHex(hue, 0.42, 0.72),
      emissive: hslToHex(hue, 0.55, 0.55),
      emissiveIntensity: 1.05,
    };
  }
  if (node.kind === 'workspace' && node.tone === 'attention') {
    return { base: 0xffc078, emissive: 0xffa040, emissiveIntensity: 1.15 };
  }
  if (node.kind === 'workspace' && node.tone === 'critical') {
    return { base: 0xff8a8a, emissive: 0xff5050, emissiveIntensity: 1.3 };
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
