import { describe, expect, it } from 'vitest';

import { vaxonAffirmReplyCta, vaxonLineAsksForReply } from './vaxon-reply-prompt';

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
  });

  it('ignores plain narration', () => {
    expect(vaxonLineAsksForReply('Watch connected. Runtime looks nominal.')).toBe(false);
  });
});

describe('vaxonAffirmReplyCta', () => {
  it('specializes Affirm CTA for Attention invites', () => {
    expect(vaxonAffirmReplyCta('Open Attention for DashPro Sentry critical?')).toBe(
      'Yes — open Attention',
    );
  });
});
