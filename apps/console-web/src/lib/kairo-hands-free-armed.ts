import type { OperatorPresenceSettings } from '../contracts/canonical';

import { isKairoMediaUnlocked } from './kairo-audio-unlock';

/** Hands-free / duplex is only truthful once media playback (and mic path) is unlocked. */
export function isKairoHandsFreeArmed(
  settings: Pick<
    OperatorPresenceSettings,
    'hands_free_enabled' | 'proactive_duplex_enabled' | 'privacy_mode'
  >,
  mediaUnlocked: boolean = isKairoMediaUnlocked(),
): boolean {
  if (settings.privacy_mode) {
    return false;
  }
  if (!mediaUnlocked) {
    return false;
  }
  return settings.hands_free_enabled === true || settings.proactive_duplex_enabled === true;
}

export function shouldEnableKairoHandsFreeLoop(
  settings: Pick<
    OperatorPresenceSettings,
    'hands_free_enabled' | 'proactive_duplex_enabled' | 'privacy_mode'
  >,
  mediaUnlocked: boolean = isKairoMediaUnlocked(),
): boolean {
  // Ambient listen (hands-free or duplex) only after media unlock —
  // matches isKairoHandsFreeArmed so the mic never starts while the banner is up.
  return isKairoHandsFreeArmed(settings, mediaUnlocked);
}
