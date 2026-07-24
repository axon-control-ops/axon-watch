/** Galaxy-aligned HUD holo tones (Brain Galaxy ice / signal / connector). */

export type HudHoloTone = 'nominal' | 'attention' | 'critical';

export type HudHoloSignal = {
  id: string;
  tone: HudHoloTone;
  selected?: boolean;
  /** 0–1 relative glow weight (default 1). */
  weight?: number;
};

export const HUD_HOLO_EDGE: Record<HudHoloTone, string> = {
  nominal: '#00f2ff',
  attention: '#ffa040',
  critical: '#ff6aa8',
};

export const HUD_HOLO_FILL: Record<HudHoloTone, string> = {
  nominal: '#00c8e6',
  attention: '#ffa040',
  critical: '#ff6aa8',
};

export const HUD_HOLO_FILL_OPACITY: Record<HudHoloTone, number> = {
  nominal: 0.12,
  attention: 0.14,
  critical: 0.16,
};

const TONE_RANK: Record<HudHoloTone, number> = {
  nominal: 0,
  attention: 1,
  critical: 2,
};

export function worstHudHoloTone(tones: ReadonlyArray<HudHoloTone | null | undefined>): HudHoloTone {
  let worst: HudHoloTone = 'nominal';
  for (const tone of tones) {
    if (!tone) {
      continue;
    }
    if (TONE_RANK[tone] > TONE_RANK[worst]) {
      worst = tone;
    }
  }
  return worst;
}

export function fleetHealthToHoloTone(
  health: 'nominal' | 'attention' | 'critical' | string | null | undefined,
): HudHoloTone {
  if (health === 'critical') {
    return 'critical';
  }
  if (health === 'attention') {
    return 'attention';
  }
  return 'nominal';
}

export function taskBoardBucketToHoloTone(
  bucket: 'open' | 'leased' | 'done' | 'failed' | string,
): HudHoloTone {
  if (bucket === 'failed') {
    return 'critical';
  }
  if (bucket === 'leased' || bucket === 'open') {
    return 'attention';
  }
  return 'nominal';
}
