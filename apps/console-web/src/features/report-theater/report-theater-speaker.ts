import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import { deliverSpokenOperatorAlert } from '../../lib/spoken-alert-delivery';
import {
  employeeVoiceSpeaker,
  vaxonVoiceSpeaker,
  type KairoVoiceSpeaker,
} from '../../lib/kairo-voice-utterance';
import { setReportTheaterSpeakerName } from './report-theater-state';

type ReportTheaterVoiceShell = {
  companyEmployeesForCurrentWorkspace: CompanyEmployeeRecord[];
};

function resolveTheaterSpeaker(
  shell: ReportTheaterVoiceShell,
  speakerName?: string | null,
): KairoVoiceSpeaker {
  const normalizedName = speakerName?.trim().toLowerCase();
  const employee = normalizedName
    ? shell.companyEmployeesForCurrentWorkspace.find(
        (row) => row.name.trim().toLowerCase() === normalizedName,
      )
    : null;
  return employee ? employeeVoiceSpeaker(employee) : vaxonVoiceSpeaker();
}

/**
 * Stand-up turns use the same Mission Control delivery hop:
 * deliverSpokenOperatorAlert → speakKairoLine → Azure queue (default timeout).
 * Voice Deck is bypassed so employee neural voices are preserved.
 */
export async function speakReportTheaterTurn(
  shell: ReportTheaterVoiceShell,
  line: string,
  _operatorPrompt: string,
  speakerName?: string | null,
  onPlaybackStart?: () => void,
): Promise<void> {
  const trimmed = line.trim();
  if (!trimmed) {
    onPlaybackStart?.();
    return;
  }
  const speaker = resolveTheaterSpeaker(shell, speakerName);
  const channel = await deliverSpokenOperatorAlert(
    {
      eligible: true,
      reason: 'report_theater_turn',
      signal_id: null,
      message: trimmed,
    },
    typeof sessionStorage !== 'undefined' ? sessionStorage : {
      getItem: () => null,
      setItem: () => undefined,
    },
    {
      priority: 'alert',
      dedupe: false,
      queueUntilUnlock: false,
      openFollowupWindow: false,
      directPlayback: true,
      allowDuringReportTheater: true,
      speaker,
      azureVoiceId: speaker.azureVoiceId,
      onPlaybackStart: () => {
        setReportTheaterSpeakerName(speaker.name);
        onPlaybackStart?.();
      },
    },
  );
  if (channel === 'skipped') {
    setReportTheaterSpeakerName(speaker.name);
    onPlaybackStart?.();
  }
}
