import { describe, expect, it } from 'vitest';

import {
  humanizeLeadFailureDetail,
  looksLikeLeadCheckinReport,
  parseLeadCheckinReport,
} from './lead-checkin-card';
import { parseAgentTranscriptBlocks } from './agent-transcript-blocks';

const SAMPLE = [
  'Lead check-in: scheduled team health pass.',
  'Findings: 1 · Assignments created: 0',
  '',
  '1. [failed_shift] Priya (frontend) last shift failed (→ frontend)',
  '   Lane B finalization failed: review_ready/complete blocked: acceptance_evidence did not pass [Gate 6] | acceptance=fail - policy=out_of_scope - mode=contract - paths=22 - .. [run=run_5e4855fc6e75]',
].join('\n');

describe('lead-checkin-card', () => {
  it('detects the deterministic Lead check-in dump', () => {
    expect(looksLikeLeadCheckinReport(SAMPLE)).toBe(true);
    expect(looksLikeLeadCheckinReport('Here is a normal reply.')).toBe(false);
  });

  it('humanizes Gate 6 / out-of-scope dumps', () => {
    expect(
      humanizeLeadFailureDetail(
        'Lane B finalization failed: acceptance_evidence did not pass [Gate 6] | policy=out_of_scope',
      ),
    ).toMatch(/out of scope/i);
  });

  it('parses findings, next steps, and options', () => {
    const card = parseLeadCheckinReport(SAMPLE);
    expect(card).not.toBeNull();
    expect(card?.findingCount).toBe(1);
    expect(card?.assignmentCount).toBe(0);
    expect(card?.findings[0]?.title).toContain('Priya');
    expect(card?.findings[0]?.detail).toMatch(/acceptance/i);
    expect(card?.nextSteps[0]).toMatch(/Priya/i);
    expect(card?.options.some((option) => /Retry Priya/i.test(option.label))).toBe(true);
    expect(card?.options.some((option) => /Recovery Center/i.test(option.label))).toBe(true);
  });

  it('upgrades check-in dumps into a dedicated transcript card', () => {
    expect(parseAgentTranscriptBlocks(SAMPLE).map((segment) => segment.kind)).toEqual([
      'lead-checkin',
    ]);
  });

  it('does not make an all-clear health pass into a decision card', () => {
    const clear = parseLeadCheckinReport(
      ['Lead check-in: scheduled team health pass.', 'Findings: 0 · Assignments created: 0'].join('\n'),
    );
    expect(clear?.options).toEqual([]);
  });
});
