/** Galaxy-aligned HUD holo tones (Brain Galaxy ice / signal / connector). */

export type HudHoloTone = 'nominal' | 'attention' | 'critical';

export const HUD_HOLO_EDGE: Record<HudHoloTone, string> = {
  nominal: '#7aebff',
  attention: '#ffa040',
  critical: '#ff6aa8',
};

export const HUD_HOLO_FILL: Record<HudHoloTone, string> = {
  nominal: '#5a9fff',
  attention: '#ffa040',
  critical: '#ff6aa8',
};

export const HUD_HOLO_FILL_OPACITY: Record<HudHoloTone, number> = {
  nominal: 0.12,
  attention: 0.14,
  critical: 0.16,
};
