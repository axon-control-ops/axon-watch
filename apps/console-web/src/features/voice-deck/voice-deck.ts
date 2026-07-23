import type { SpokenAlertEligibility } from '../../contracts/canonical';

import { speakKairoLine } from '../../lib/kairo-voice-playback';
import { registerVoiceDeckSpokenAlertHandler } from '../../lib/spoken-alert-delivery';
import { vaxonVoiceSpeaker } from '../../lib/kairo-voice-utterance';

export async function handleVoiceDeckSpokenAlert(
  alert: SpokenAlertEligibility,
): Promise<boolean> {
  if (!alert.eligible || !alert.message.trim()) {
    return false;
  }

  // Azure-first: browser speechSynthesis is only a diagnosed fallback inside
  // kairo-voice-playback when Azure fetch/play fails (WebKit autoplay, vault, etc.).
  const speaker = vaxonVoiceSpeaker();
  // #region agent log
  fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'fc0b35'},body:JSON.stringify({sessionId:'fc0b35',runId:'speaker-avatar',hypothesisId:'D',location:'voice-deck.ts:handleVoiceDeckSpokenAlert',message:'voice deck alert with VAXON speaker',data:{speakerKind:speaker.kind,messagePreview:alert.message.trim().slice(0,80)},timestamp:Date.now()})}).catch(()=>{});
  // #endregion
  await speakKairoLine(alert.message.trim(), { priority: 'alert', speaker });
  return true;
}

export function registerVoiceDeckOnBoot(): void {
  registerVoiceDeckSpokenAlertHandler((alert) => handleVoiceDeckSpokenAlert(alert));
}
