import { describe, expect, it } from 'vitest';

import {
  buildReportTheaterStages,
  normalizeReportTheaterSections,
  parseReportSectionsFromReply,
  pickReportTheaterActions,
} from './report-theater-model';

describe('report-theater-model', () => {
  it('builds five staged panels from structured sections', () => {
    const stages = buildReportTheaterStages(
      normalizeReportTheaterSections({
        attention: ['DashPro CI failed'],
        work_in_flight: ['Dana is executing'],
        lead_rollups: ['Priya handoff ready'],
        fleet: ['fleet looks nominal across six workspaces'],
        next_move: 'Open the Lead rollup',
      }),
    );
    expect(stages).toHaveLength(5);
    expect(stages[0]?.title).toBe('Attention');
    expect(stages[4]?.lines[0]).toContain('Lead rollup');
  });

  it('parses a flat stand-up reply when sections are missing', () => {
    const sections = parseReportSectionsFromReply(
      "Here's the stand-up. Attention: DashPro needs attention. Work in flight: Dana is executing. Lead rollups: none verified yet. Fleet: fleet looks nominal across six workspaces. Next move: Open VAXON for the Lead rollup.",
    );
    expect(sections.attention[0]).toContain('DashPro');
    expect(sections.work_in_flight[0]).toContain('Dana');
    expect(sections.next_move).toContain('Lead rollup');
  });

  it('caps next-step actions', () => {
    expect(
      pickReportTheaterActions(
        [
          {
            action_id: 'a1',
            kind: 'review_signal',
            title: 'One',
            detail: '',
            workspace_id: null,
            run_id: null,
            signal_id: 's1',
          },
          {
            action_id: 'a2',
            kind: 'inspect_runtime',
            title: 'Two',
            detail: '',
            workspace_id: null,
            run_id: null,
            signal_id: null,
          },
          {
            action_id: 'a3',
            kind: 'approve_run',
            title: 'Three',
            detail: '',
            workspace_id: null,
            run_id: 'r1',
            signal_id: null,
          },
          {
            action_id: 'a4',
            kind: 'resume_run',
            title: 'Four',
            detail: '',
            workspace_id: null,
            run_id: 'r2',
            signal_id: null,
          },
        ],
        3,
      ),
    ).toHaveLength(3);
  });
});
