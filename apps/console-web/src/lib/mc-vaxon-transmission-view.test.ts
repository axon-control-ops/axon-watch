import { describe, expect, it } from 'vitest';

import { resolveVaxonTransmissionView } from './mc-vaxon-transmission-view';

describe('resolveVaxonTransmissionView', () => {
  it('shows standby empty copy when quiet', () => {
    expect(resolveVaxonTransmissionView({})).toEqual({
      mode: 'standby',
      eyebrow: 'Awaiting transmission',
      body: 'Ask VAXON here — or say REPORT for a stand-up.',
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

  it('restores CI spelling for on-screen transmission copy', () => {
    expect(
      resolveVaxonTransmissionView({
        spokenText: 'Android C I C D Pipeline failed on main.',
        speaking: true,
      }).body,
    ).toBe('Android CI/CD Pipeline failed on main.');
  });

  it('holds an unanswered decision above later live-status copy', () => {
    expect(
      resolveVaxonTransmissionView({
        pendingDecision: 'Open Attention for the Android CI/CD failure?',
        spokenText: 'AUTONOMOUS ON · attending Mission Control',
        speaking: true,
      }),
    ).toMatchObject({
      mode: 'locked',
      eyebrow: 'Decision needed',
      body: 'Open Attention for the Android CI/CD failure?',
    });
  });
});
