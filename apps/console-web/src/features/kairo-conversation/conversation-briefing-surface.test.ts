import { describe, expect, it, beforeEach } from 'vitest';

import {
  BRIEFING_SURFACE_OFFER_WINDOW_MS,
  clearBriefingSurfaceOffer,
  isBriefingSurfaceOfferActive,
  mentionsBriefingSurfaceOffer,
  scheduleBriefingSurfaceOffer,
  shouldOpenBriefingFromFollowup,
} from './conversation-briefing-surface';

describe('conversation-briefing-surface', () => {
  beforeEach(() => {
    clearBriefingSurfaceOffer();
  });

  it('detects model offers to surface the briefing', () => {
    expect(mentionsBriefingSurfaceOffer('Shall I pull it to the front?')).toBe(true);
    expect(mentionsBriefingSurfaceOffer('Systems nominal.')).toBe(false);
  });

  it('opens briefing on yes while the offer window is active', () => {
    scheduleBriefingSurfaceOffer(1_000);
    expect(shouldOpenBriefingFromFollowup('yes', 2_000)).toBe(true);
    expect(shouldOpenBriefingFromFollowup('pull it to the front', 2_000)).toBe(true);
  });

  it('keeps the offer open long enough for the operator to decide', () => {
    scheduleBriefingSurfaceOffer(1_000);
    expect(isBriefingSurfaceOfferActive(41_000)).toBe(true);
  });

  it('ignores yes after the offer window expires', () => {
    scheduleBriefingSurfaceOffer(1_000);
    const expired = 1_000 + BRIEFING_SURFACE_OFFER_WINDOW_MS;
    expect(isBriefingSurfaceOfferActive(expired)).toBe(false);
    expect(shouldOpenBriefingFromFollowup('yes', expired)).toBe(false);
  });
});
