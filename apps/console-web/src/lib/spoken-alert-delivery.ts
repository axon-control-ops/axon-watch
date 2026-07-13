import type { SpokenAlertEligibility } from '../contracts/canonical';

import { speakKairoLine } from './kairo-voice-playback';
import type { KairoVoicePriority } from './kairo-voice-queue';
import { shouldSpeakAlert, spokenAlertDedupeKey } from './operator-presence';

export type SpokenAlertDeliveryChannel = 'voice_deck' | 'azure' | 'browser' | 'skipped';

export type VoiceDeckSpokenAlertHandler = (
  alert: SpokenAlertEligibility,
) => boolean | Promise<boolean>;

export type DeliverSpokenAlertOptions = {
  /** Default `alert`. Use `narration` for run milestones / live thinking. */
  priority?: KairoVoicePriority;
  /** Allow explicit triggers to speak even if a matching alert was already marked spoken. */
  dedupe?: boolean;
};

let voiceDeckSpokenAlertHandler: VoiceDeckSpokenAlertHandler | null = null;

export function registerVoiceDeckSpokenAlertHandler(
  handler: VoiceDeckSpokenAlertHandler | null,
): void {
  voiceDeckSpokenAlertHandler = handler;
}

export function getVoiceDeckSpokenAlertHandler(): VoiceDeckSpokenAlertHandler | null {
  return voiceDeckSpokenAlertHandler;
}

export async function deliverSpokenOperatorAlert(
  alert: SpokenAlertEligibility,
  storage: Pick<Storage, 'getItem' | 'setItem'> = sessionStorage,
  options: DeliverSpokenAlertOptions = {},
): Promise<SpokenAlertDeliveryChannel> {
  // #region agent log
  void import('./axon-debug-session-log').then(({ axonDebugSessionLog }) => {
    axonDebugSessionLog({
      hypothesisId: 'H5',
      location: 'spoken-alert-delivery.ts:deliverSpokenOperatorAlert',
      message: 'voice delivery attempted',
      data: {
        priority: options.priority ?? 'alert',
        reason: alert.reason,
        signalId: alert.signal_id ?? '',
        preview: alert.message.slice(0, 180),
        looksLikeReproduceSteps:
          /^\s*\d+\.\s+/m.test(alert.message) || /\b1\.\s+/.test(alert.message),
      },
    });
  });
  // #endregion
  if (options.dedupe !== false && !shouldSpeakAlert(alert, storage)) {
    // #region agent log
    void import('./axon-debug-session-log').then(({ axonDebugSessionLog }) => {
      axonDebugSessionLog({
        hypothesisId: 'H5',
        location: 'spoken-alert-delivery.ts:deliverSpokenOperatorAlert',
        message: 'voice delivery skipped by dedupe',
        data: { reason: alert.reason, signalId: alert.signal_id ?? '' },
      });
    });
    // #endregion
    return 'skipped';
  }

  if (voiceDeckSpokenAlertHandler && (options.priority ?? 'alert') === 'alert') {
    const handled = await voiceDeckSpokenAlertHandler(alert);
    if (handled) {
      return 'voice_deck';
    }
  }

  const result = await speakKairoLine(alert.message, {
    priority: options.priority ?? 'alert',
  });
  // #region agent log
  fetch('http://127.0.0.1:7852/ingest/0173158c-fd82-46b4-a14c-d55e0685ee25',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'df24bc'},body:JSON.stringify({sessionId:'df24bc',runId:alert.signal_id??'unknown',hypothesisId:'R4',location:'spoken-alert-delivery.ts:afterPlayback',message:'spoken alert playback completed',data:{reason:alert.reason,signalId:alert.signal_id??'',line:alert.message.slice(0,280),priority:options.priority??'alert',engine:result.engine},timestamp:Date.now()})}).catch(()=>{});
  // #endregion
  if (result.engine === 'azure') {
    return 'azure';
  }
  if (result.engine === 'browser') {
    return 'browser';
  }
  return 'skipped';
}

export { spokenAlertDedupeKey };
