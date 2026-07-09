import { describe, expect, it, beforeEach } from 'vitest';

import {
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

  it('ignores yes after the offer window expires', () => {
    scheduleBriefingSurfaceOffer(1_000);
    expect(isBriefingSurfaceOfferActive(40_000)).toBe(false);
    expect(shouldOpenBriefingFromFollowup('yes', 40_000)).toBe(false);
  });
});
