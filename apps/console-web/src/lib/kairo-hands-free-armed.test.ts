import { describe, expect, it } from 'vitest';

import {
  applyJarvisDuplexPreset,
  defaultOperatorPresenceSettings,
} from './operator-presence-settings';
import {
  isKairoHandsFreeArmed,
  shouldEnableKairoHandsFreeLoop,
} from './kairo-hands-free-armed';

describe('jarvis duplex preset', () => {
  it('enables hands-free + spoken alerts and clears privacy', () => {
    const next = applyJarvisDuplexPreset(
      {
        ...defaultOperatorPresenceSettings(),
        privacy_mode: true,
        spoken_alerts_enabled: false,
        kairo_narration: 'off',
      },
      true,
    );
    expect(next.proactive_duplex_enabled).toBe(true);
    expect(next.hands_free_enabled).toBe(true);
    expect(next.spoken_alerts_enabled).toBe(true);
    expect(next.privacy_mode).toBe(false);
    expect(next.kairo_narration).toBe('conversational');
    expect(next.stt_mode).toBe('cloud');
  });

  it('can disable duplex without forcing hands-free off', () => {
    const next = applyJarvisDuplexPreset(
      {
        ...defaultOperatorPresenceSettings(),
        proactive_duplex_enabled: true,
        hands_free_enabled: true,
      },
      false,
    );
    expect(next.proactive_duplex_enabled).toBe(false);
    expect(next.hands_free_enabled).toBe(true);
  });
});

describe('hands-free armed', () => {
  it('requires media unlock before claiming hands-free HUD', () => {
    const settings = {
      ...defaultOperatorPresenceSettings(),
      hands_free_enabled: true,
    };
    expect(isKairoHandsFreeArmed(settings, false)).toBe(false);
    expect(isKairoHandsFreeArmed(settings, true)).toBe(true);
  });

  it('enables the loop for duplex only after unlock', () => {
    const duplex = {
      ...defaultOperatorPresenceSettings(),
      proactive_duplex_enabled: true,
      hands_free_enabled: false,
    };
    expect(shouldEnableKairoHandsFreeLoop(duplex, false)).toBe(false);
    expect(shouldEnableKairoHandsFreeLoop(duplex, true)).toBe(true);
  });

  it('does not start ambient listen for hands-free until unlock (JARVIS preset)', () => {
    const preset = applyJarvisDuplexPreset(defaultOperatorPresenceSettings(), true);
    expect(shouldEnableKairoHandsFreeLoop(preset, false)).toBe(false);
    expect(shouldEnableKairoHandsFreeLoop(preset, true)).toBe(true);
    expect(isKairoHandsFreeArmed(preset, false)).toBe(false);
    expect(isKairoHandsFreeArmed(preset, true)).toBe(true);
  });
});
