import { describe, expect, it } from 'vitest';

import {
  isSpokenLineLiveEvent,
  resolveSpokenLineSpeaker,
  spokenLineDedupeReason,
} from './spoken-line-live-event';

describe('spoken-line-live-event', () => {
  it('accepts spoken_line payloads with a speakable line', () => {
    expect(
      isSpokenLineLiveEvent({
        type: 'spoken_line',
        line: 'Dana here. Soren just completed.',
        receipt_id: 'lead_takeover_voice_run_1',
      }),
    ).toBe(true);
    expect(isSpokenLineLiveEvent({ type: 'spoken_line', line: '  ' })).toBe(false);
    expect(isSpokenLineLiveEvent({ type: 'spoken_briefing' })).toBe(false);
  });

  it('resolves Lead speakers as employees and VAXON as console', () => {
    const lead = resolveSpokenLineSpeaker({
      type: 'spoken_line',
      line: 'Lead rollup',
      speaker_name: 'Dana',
      speaker_role: 'lead',
      speaker_employee_id: 'employee-lead',
    });
    expect(lead).toMatchObject({
      kind: 'employee',
      id: 'employee-lead',
      name: 'Dana',
    });

    const vaxon = resolveSpokenLineSpeaker({
      type: 'spoken_line',
      line: 'VAXON flash',
      speaker_name: 'VAXON',
      speaker_role: 'vaxon',
    });
    expect(vaxon.kind).toBe('vaxon');
  });

  it('dedupes by receipt id when present', () => {
    expect(
      spokenLineDedupeReason({
        type: 'spoken_line',
        line: 'hello',
        receipt_id: 'lead_takeover_voice_run_9',
      }),
    ).toBe('spoken_line:lead_takeover_voice_run_9');
  });
});
