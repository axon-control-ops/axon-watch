import {
  employeeVoiceSpeaker,
  vaxonVoiceSpeaker,
  type KairoVoiceSpeaker,
} from './kairo-voice-utterance';

export type SpokenLineLiveEvent = {
  type: 'spoken_line';
  line: string;
  receipt_id?: string;
  signal_id?: string;
  workspace_id?: string;
  kind?: string;
  speaker_name?: string;
  speaker_role?: string;
  speaker_employee_id?: string;
};

export function isSpokenLineLiveEvent(
  value: unknown,
): value is SpokenLineLiveEvent {
  if (!value || typeof value !== 'object') {
    return false;
  }
  const row = value as Record<string, unknown>;
  return row.type === 'spoken_line' && typeof row.line === 'string' && Boolean(row.line.trim());
}

export function resolveSpokenLineSpeaker(event: SpokenLineLiveEvent): KairoVoiceSpeaker {
  const role = (event.speaker_role ?? '').trim().toLowerCase();
  if (role === 'vaxon' || role === 'operator') {
    return vaxonVoiceSpeaker({ name: event.speaker_name?.trim() || 'VAXON' });
  }
  const employeeId =
    event.speaker_employee_id?.trim() ||
    `role:${(event.speaker_role || 'lead').trim().toLowerCase() || 'lead'}`;
  return employeeVoiceSpeaker({
    employee_id: employeeId,
    name: event.speaker_name?.trim() || 'Lead',
    role: event.speaker_role?.trim() || 'lead',
    role_label: event.speaker_role?.trim() || 'Lead',
  });
}

export function spokenLineDedupeReason(event: SpokenLineLiveEvent): string {
  const receipt = event.receipt_id?.trim();
  if (receipt) {
    return `spoken_line:${receipt}`;
  }
  const kind = (event.kind || 'lead_takeover').trim() || 'lead_takeover';
  return `spoken_line:${kind}:${event.line.trim().slice(0, 80)}`;
}
