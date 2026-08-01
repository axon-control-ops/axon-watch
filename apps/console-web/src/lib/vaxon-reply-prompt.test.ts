import { describe, expect, it } from 'vitest';

import {
  isAffirmativeOperatorReply,
  spokenLineAsksForRetry,
  vaxonAffirmReplyCta,
  vaxonLineAsksForReply,
  vaxonLineNeedsIntervention,
} from './vaxon-reply-prompt';

describe('vaxonLineAsksForReply', () => {
  it('treats trailing questions as reply prompts', () => {
    expect(vaxonLineAsksForReply('Online and listening, sir. What shall we focus on?')).toBe(
      true,
    );
    expect(
      vaxonLineAsksForReply('Heads up — DashPro Sentry critical. Open Attention for DashPro Sentry critical?'),
    ).toBe(true);
  });

  it('matches invite phrasing without requiring a trailing question mark', () => {
    expect(vaxonLineAsksForReply('Shall I open Attention for the top signal')).toBe(true);
    expect(vaxonLineAsksForReply('Would you like me to triage DashPro next')).toBe(true);
    expect(
      vaxonLineAsksForReply(
        'I can try again, or explain what happened — your call.',
      ),
    ).toBe(true);
  });

  it('ignores plain narration', () => {
    expect(vaxonLineAsksForReply('Watch connected. Runtime looks nominal.')).toBe(false);
  });

  it('treats handoff / switch-there lines as needing operator intervention', () => {
    const handoff =
      "Handoff to Axon Watch is open, switch there and finish 'Control-plane fix for DashPro Lead blocker'.";
    expect(vaxonLineNeedsIntervention(handoff)).toBe(true);
    expect(vaxonLineAsksForReply(handoff)).toBe(true);
    expect(vaxonAffirmReplyCta(handoff)).toBe('Yes — switch & attend');
  });
});

describe('spokenLineAsksForRetry', () => {
  it('matches teammate try-again invites', () => {
    expect(spokenLineAsksForRetry('I can try again, or explain what happened — your call.')).toBe(
      true,
    );
    expect(spokenLineAsksForRetry('Hit Try again when you want another go')).toBe(true);
  });
});

describe('vaxonAffirmReplyCta', () => {
  it('specializes Affirm CTA for Attention invites', () => {
    expect(vaxonAffirmReplyCta('Open Attention for DashPro Sentry critical?')).toBe(
      'Yes — open Attention',
    );
  });

  it('offers Try again when the spoken line asks for a retry', () => {
    expect(vaxonAffirmReplyCta('I can try again, or explain what happened — your call.')).toBe(
      'Try again',
    );
  });
});

describe('isAffirmativeOperatorReply', () => {
  it('accepts short affirmations and Try again', () => {
    expect(isAffirmativeOperatorReply('Try again')).toBe(true);
    expect(isAffirmativeOperatorReply('yes')).toBe(true);
    expect(isAffirmativeOperatorReply('no')).toBe(false);
  });
});
