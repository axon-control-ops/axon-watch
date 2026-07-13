import type { SpokenAlertEligibility } from '../../contracts/canonical';

import { speakKairoLine } from '../../lib/kairo-voice-playback';
import { registerVoiceDeckSpokenAlertHandler } from '../../lib/spoken-alert-delivery';

export async function handleVoiceDeckSpokenAlert(
  alert: SpokenAlertEligibility,
): Promise<boolean> {
  if (!alert.eligible || !alert.message.trim()) {
    return false;
  }

  await speakKairoLine(alert.message.trim(), { priority: 'alert', preferBrowser: true });
  return true;
}

export function registerVoiceDeckOnBoot(): void {
  registerVoiceDeckSpokenAlertHandler((alert) => handleVoiceDeckSpokenAlert(alert));
}
