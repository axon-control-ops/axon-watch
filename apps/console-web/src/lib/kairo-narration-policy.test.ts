import { describe, expect, it } from 'vitest';

import {
  effectiveKairoNarration,
  mapMilestoneToSpeakEvent,
  shouldNarrateAgentEvent,
} from './kairo-narration-policy';

describe('kairo-narration-policy', () => {
  it('forces off in IDE quiet unless conversational is selected', () => {
    expect(
      effectiveKairoNarration({
        settingsNarration: 'minimal',
        layoutMode: 'ide',
        idePresenceProfile: 'quiet',
      }),
    ).toBe('off');

    expect(
      effectiveKairoNarration({
        settingsNarration: 'conversational',
        layoutMode: 'ide',
        idePresenceProfile: 'quiet',
      }),
    ).toBe('conversational');
  });

  it('preserves settings narration outside IDE quiet tier', () => {
    expect(
      effectiveKairoNarration({
        settingsNarration: 'minimal',
        layoutMode: 'ide',
        idePresenceProfile: 'assist',
      }),
    ).toBe('minimal');

    expect(
      effectiveKairoNarration({
        settingsNarration: 'conversational',
        layoutMode: 'operator',
        idePresenceProfile: 'quiet',
      }),
    ).toBe('conversational');
  });

  it('gates agent milestones by narration level', () => {
    expect(
      shouldNarrateAgentEvent({ eventKey: 'start', narration: 'off' }),
    ).toBe(false);

    expect(
      shouldNarrateAgentEvent({ eventKey: 'tool:0', narration: 'minimal' }),
    ).toBe(false);

    expect(
      shouldNarrateAgentEvent({ eventKey: 'done', narration: 'minimal' }),
    ).toBe(true);

    expect(
      shouldNarrateAgentEvent({ eventKey: 'tool:0', narration: 'conversational' }),
    ).toBe(false);

    expect(
      shouldNarrateAgentEvent({ eventKey: 'start', narration: 'conversational' }),
    ).toBe(true);
  });

  it('maps milestone keys to speak event types', () => {
    expect(mapMilestoneToSpeakEvent('start')).toBe('agent_start');
    expect(mapMilestoneToSpeakEvent('thinking:0')).toBe('thinking');
    expect(mapMilestoneToSpeakEvent('tool:1')).toBe('tool');
    expect(mapMilestoneToSpeakEvent('edit:2')).toBe('edit');
    expect(mapMilestoneToSpeakEvent('done')).toBe('done');
  });
});
