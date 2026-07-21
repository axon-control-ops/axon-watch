import type { SpokenAlertEligibility } from '../../contracts/canonical';

import { speakKairoLine } from '../../lib/kairo-voice-playback';
import { registerVoiceDeckSpokenAlertHandler } from '../../lib/spoken-alert-delivery';

export async function handleVoiceDeckSpokenAlert(
  alert: SpokenAlertEligibility,
): Promise<boolean> {
  if (!alert.eligible || !alert.message.trim()) {
    return false;
  }

  // Azure-first: browser speechSynthesis is only a diagnosed fallback inside
  // kairo-voice-playback when Azure fetch/play fails (WebKit autoplay, vault, etc.).
  await speakKairoLine(alert.message.trim(), { priority: 'alert' });
  return true;
}

export function registerVoiceDeckOnBoot(): void {
  registerVoiceDeckSpokenAlertHandler((alert) => handleVoiceDeckSpokenAlert(alert));
}
