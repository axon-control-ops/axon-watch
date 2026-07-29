import { describe, expect, it } from 'vitest';

import { buildReportTheaterAttendees } from './report-theater-attendees';

describe('report-theater-attendees', () => {
  it('puts VAXON first and highlights named leads', () => {
    const attendees = buildReportTheaterAttendees({
      employees: [
        {
          employee_id: 'e1',
          name: 'Mira',
          role: 'lead',
          role_label: 'Lead',
          primary: true,
          status: 'idle',
          active_run_id: null,
          last_outcome: null,
          azure_voice_id: null,
          workspace_id: 'w1',
        } as never,
        {
          employee_id: 'e2',
          name: 'Reed',
          role: 'backend',
          role_label: 'Backend',
          primary: false,
          status: 'idle',
          active_run_id: null,
          last_outcome: 'completed',
          azure_voice_id: null,
          workspace_id: 'w1',
        } as never,
      ],
      activeLines: ['Reed (Backend) just wrapped'],
      activeSpeakerName: 'Mira',
      max: 5,
    });
    expect(attendees[0]?.kind).toBe('vaxon');
    expect(attendees.some((row) => row.name === 'Reed' && row.speaking)).toBe(false);
    expect(attendees.some((row) => row.name === 'Mira' && row.lead && row.speaking)).toBe(true);
  });

  it('keeps status chips locked to stage and active speaker', () => {
    const employees = [
      {
        employee_id: 'e1',
        name: 'Dana',
        role: 'lead',
        role_label: 'Lead',
        primary: true,
        status: 'idle',
        active_run_id: null,
        last_outcome: 'completed',
        azure_voice_id: null,
        workspace_id: 'w1',
      } as never,
      {
        employee_id: 'e2',
        name: 'Marco',
        role: 'backend',
        role_label: 'Backend',
        primary: false,
        status: 'executing',
        active_run_id: 'run_1',
        last_outcome: null,
        azure_voice_id: null,
        workspace_id: 'w1',
      } as never,
    ];

    const reporting = buildReportTheaterAttendees({
      employees,
      activeLines: ['Dana: Commit landed'],
      stageId: 'lead_rollups',
      activeSpeakerName: 'Dana',
      max: 5,
    });
    expect(reporting.find((row) => row.name === 'Dana')?.statusLine).toBe('reporting');
    expect(reporting.find((row) => row.kind === 'vaxon')?.statusLine).toBe('listening');

    const work = buildReportTheaterAttendees({
      employees,
      activeLines: ['Marco (Backend) is executing'],
      stageId: 'work_in_flight',
      activeSpeakerName: null,
      max: 5,
    });
    expect(work.find((row) => row.name === 'Marco')?.statusLine).toBe('assigned');

    const moving = buildReportTheaterAttendees({
      employees,
      activeLines: ["I'll open Vault next"],
      stageId: 'next_move',
      activeSpeakerName: null,
      max: 5,
    });
    expect(moving.find((row) => row.kind === 'vaxon')?.statusLine).toBe('moving');
    expect(moving.find((row) => row.name === 'Dana')?.statusLine).toBe('standing by');
  });
});
