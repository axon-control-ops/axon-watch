import { describe, expect, it } from 'vitest';

import { resolveVaxonTransmissionView } from './mc-vaxon-transmission-view';

describe('resolveVaxonTransmissionView', () => {
  it('shows standby empty copy when quiet', () => {
    expect(resolveVaxonTransmissionView({})).toEqual({
      mode: 'standby',
      eyebrow: 'Awaiting transmission',
      body: 'Ask VAXON here — replies land in this dock.',
      empty: true,
    });
  });

  it('prefers live spoken text while transmitting', () => {
    expect(
      resolveVaxonTransmissionView({
        spokenText: 'Opening DashPro.',
        conversationReply: 'Opening DashPro.',
        speaking: true,
      }),
    ).toMatchObject({
      mode: 'transmitting',
      eyebrow: 'Live transmission',
      body: 'Opening DashPro.',
      empty: false,
    });
  });

  it('locks the last reply after speech ends', () => {
    expect(
      resolveVaxonTransmissionView({
        conversationReply: 'DashPro is on deck.',
      }),
    ).toMatchObject({
      mode: 'locked',
      body: 'DashPro is on deck.',
    });
  });
});
