import type { KairoNarrationLevel } from '../../../contracts/canonical';
import type { WorkspaceRecord } from '../../../contracts/canonical';
import type { LiveEventPayload } from '../../../lib/live-events-session';
import {
  isSpokenLineLiveEvent,
  resolveSpokenLineSpeaker,
  spokenLineDedupeReason,
} from '../../../lib/spoken-line-live-event';
import { unlockKairoAudioPlayback } from '../../../lib/kairo-audio-unlock';
import { deliverSpokenOperatorAlert } from '../../../lib/spoken-alert-delivery';
import { reportTheaterOpen } from '../../../features/report-theater/report-theater-state';

type SpeakSpokenLineInput = {
  event: LiveEventPayload;
  voiceDeliveryAllowed: () => boolean;
  privacyMode: boolean;
  spokenAlertsEnabled: boolean;
  narrationLevel: KairoNarrationLevel;
  currentWorkspace: WorkspaceRecord | null;
  sessionStorage: Storage;
};

/** Speak an explicit control-plane spoken_line event (Lead takeover / synthesis). */
export async function speakSpokenLineEvent(input: SpeakSpokenLineInput): Promise<void> {
  const event = input.event;
  if (!isSpokenLineLiveEvent(event)) {
    return;
  }
  if (!input.voiceDeliveryAllowed() || input.privacyMode) {
    return;
  }
  if (!input.spokenAlertsEnabled || input.narrationLevel === 'off') {
    return;
  }
  const eventWorkspace = event.workspace_id?.trim() ?? '';
  const currentWorkspaceId = input.currentWorkspace?.workspace_id?.trim() ?? '';
  if (eventWorkspace && currentWorkspaceId && eventWorkspace !== currentWorkspaceId) {
    return;
  }
  if (reportTheaterOpen.value) {
    return;
  }
  const line = event.line.trim();
  if (!line) {
    return;
  }
  await unlockKairoAudioPlayback();
  await deliverSpokenOperatorAlert(
    {
      eligible: true,
      reason: spokenLineDedupeReason(event),
      signal_id: event.receipt_id?.trim() || null,
      message: line,
    },
    input.sessionStorage,
    {
      speaker: resolveSpokenLineSpeaker(event),
      priority: 'conversation',
      dedupe: true,
      directPlayback: true,
      queueUntilUnlock: true,
    },
  );
}
