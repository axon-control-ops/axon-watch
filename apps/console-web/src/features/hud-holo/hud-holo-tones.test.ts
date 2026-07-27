import { describe, expect, it } from 'vitest';

import {
  HUD_HOLO_EDGE,
  HUD_HOLO_FILL,
  HUD_HOLO_FILL_OPACITY,
  fleetHealthToHoloTone,
  taskBoardBucketToHoloTone,
  worstHudHoloTone,
  type HudHoloTone,
} from './hud-holo-tones';

describe('hud-holo-tones', () => {
  it('keeps neon cyan / signal / connector palette for concept-art hologram', () => {
    const tones: HudHoloTone[] = ['nominal', 'attention', 'critical'];
    for (const tone of tones) {
      expect(HUD_HOLO_EDGE[tone].toLowerCase()).not.toBe('#00f0ff');
      expect(HUD_HOLO_FILL[tone].toLowerCase()).not.toBe('#00f0ff');
      expect(HUD_HOLO_FILL_OPACITY[tone]).toBeGreaterThan(0);
    }
    expect(HUD_HOLO_EDGE.nominal).toBe('#00f2ff');
    expect(HUD_HOLO_EDGE.critical).toBe('#ff6aa8');
  });

  it('maps fleet / task board states onto holo tones', () => {
    expect(fleetHealthToHoloTone('critical')).toBe('critical');
    expect(fleetHealthToHoloTone('attention')).toBe('attention');
    expect(fleetHealthToHoloTone('nominal')).toBe('nominal');
    expect(taskBoardBucketToHoloTone('failed')).toBe('critical');
    expect(taskBoardBucketToHoloTone('leased')).toBe('attention');
    expect(taskBoardBucketToHoloTone('done')).toBe('nominal');
  });

  it('picks the worst tone for module shell chrome', () => {
    expect(worstHudHoloTone(['nominal', 'attention', 'critical'])).toBe('critical');
    expect(worstHudHoloTone(['nominal', null, 'attention'])).toBe('attention');
    expect(worstHudHoloTone([])).toBe('nominal');
  });
});
