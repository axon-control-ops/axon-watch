import { describe, expect, it } from 'vitest';

import {
  resolveVaxonTransmissionView,
  splitTransmissionBody,
} from './mc-vaxon-transmission-view';

describe('resolveVaxonTransmissionView', () => {
  it('shows standby empty copy when quiet', () => {
    expect(resolveVaxonTransmissionView({})).toEqual({
      mode: 'standby',
      eyebrow: 'Awaiting transmission',
      body: 'Ask your second brain — or say REPORT for a stand-up.',
      summary: 'Ask your second brain — or say REPORT for a stand-up.',
      detailLines: [],
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
      summary: 'Opening DashPro.',
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
      summary: 'DashPro is on deck.',
    });
  });

  it('shows VAXON on screen even when TTS used Vekson', () => {
    expect(
      resolveVaxonTransmissionView({
        spokenText: 'Vekson is watching the fleet.',
        speaking: true,
      }),
    ).toMatchObject({
      body: 'VAXON is watching the fleet.',
    });
  });
});

describe('splitTransmissionBody', () => {
  it('keeps a short line as the summary only', () => {
    expect(splitTransmissionBody('Opening DashPro.')).toEqual({
      summary: 'Opening DashPro.',
      detailLines: [],
    });
  });

  it('maps a mega Lead-plan briefing into summary + detail', () => {
    const body =
      'Lead-team plans are waiting for you in Mission Control — Seven of them. ' +
      'Handoff to Axon Watch is open — switch there and finish “Control-plane fix for DashPro”. ' +
      'Pause more DashPro work until that closes.';
    const split = splitTransmissionBody(body);
    expect(split.summary).toMatch(/Lead-team plans are waiting/);
    expect(split.detailLines.length).toBeGreaterThan(0);
    expect(split.detailLines.some((line) => /Handoff|Pause/i.test(line))).toBe(true);
  });

  it('does not treat every capital letter as a new sentence', () => {
    const split = splitTransmissionBody(
      'Dana here. My Lead shift just failed. Ask me what to do next.',
    );
    expect(split.summary).toBe('Dana here.');
    expect(split.detailLines[0]).toMatch(/^My Lead shift/);
  });
});
