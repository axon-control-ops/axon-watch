import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import { employeeVoiceSpeaker } from '../../lib/kairo-voice-utterance';
import { setReportTheaterSpeakerName } from './report-theater-state';

type ReportTheaterVoiceShell = {
  companyEmployeesForCurrentWorkspace: CompanyEmployeeRecord[];
  speakKairoConversationLine: (
    line: string,
    options: {
      operatorPrompt: string;
      skipSpeakApi: boolean;
      priority: 'alert';
      allowDuringReportTheater: boolean;
      azureVoiceId?: string | null;
      speaker?: ReturnType<typeof employeeVoiceSpeaker> | null;
    },
  ) => Promise<void>;
};

export async function speakReportTheaterTurn(
  shell: ReportTheaterVoiceShell,
  line: string,
  operatorPrompt: string,
  speakerName?: string | null,
): Promise<void> {
  const normalizedName = speakerName?.trim().toLowerCase();
  const employee = normalizedName
    ? shell.companyEmployeesForCurrentWorkspace.find(
        (row) => row.name.trim().toLowerCase() === normalizedName,
      )
    : null;
  const speaker = employee ? employeeVoiceSpeaker(employee) : null;
  setReportTheaterSpeakerName(speaker?.name ?? 'VAXON');
  // #region agent log
  fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'speaker-voice-fix',hypothesisId:'H40,H41',location:'report-theater-speaker.ts:speakReportTheaterTurn',message:'routed stand-up turn to reporting agent voice',data:{speakerName:speaker?.name??'VAXON',azureVoiceId:speaker?.azureVoiceId??null,linePreview:line.slice(0,100)},timestamp:Date.now()})}).catch(()=>{});
  // #endregion
  await shell.speakKairoConversationLine(line, {
    operatorPrompt,
    skipSpeakApi: true,
    priority: 'alert',
    allowDuringReportTheater: true,
    azureVoiceId: speaker?.azureVoiceId,
    speaker,
  });
}
