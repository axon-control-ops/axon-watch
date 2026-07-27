import { describe, expect, it } from 'vitest';

import {
  effectiveKairoNarration,
  mapMilestoneToSpeakEvent,
  shouldNarrateAgentEvent,
  shouldNarrateProgressMilestone,
  shouldSpeakLiveThinkingBlock,
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
      shouldNarrateAgentEvent({ eventKey: 'edit:1', narration: 'minimal' }),
    ).toBe(false);

    expect(
      shouldNarrateAgentEvent({ eventKey: 'thinking:0', narration: 'minimal' }),
    ).toBe(false);

    expect(
      shouldNarrateAgentEvent({ eventKey: 'done', narration: 'minimal' }),
    ).toBe(true);

    expect(
      shouldNarrateAgentEvent({ eventKey: 'failed', narration: 'minimal' }),
    ).toBe(true);

    expect(
      shouldNarrateAgentEvent({ eventKey: 'alert:approval', narration: 'minimal' }),
    ).toBe(true);

    expect(
      shouldNarrateAgentEvent({ eventKey: 'tool:0', narration: 'conversational' }),
    ).toBe(false);

    expect(
      shouldNarrateAgentEvent({
        eventKey: 'tool:0',
        narration: 'conversational',
        narrateToolProgress: true,
      }),
    ).toBe(true);

    expect(
      shouldNarrateAgentEvent({
        eventKey: 'tool:0',
        narration: 'conversational',
        narrateToolProgress: true,
        thinkingCarriesUpdate: true,
      }),
    ).toBe(false);

    expect(
      shouldNarrateAgentEvent({ eventKey: 'thinking:1', narration: 'minimal' }),
    ).toBe(false);

    expect(
      shouldNarrateAgentEvent({ eventKey: 'start', narration: 'conversational' }),
    ).toBe(true);

    expect(
      shouldNarrateAgentEvent({ eventKey: 'done', narration: 'conversational' }),
    ).toBe(true);
  });

  it('maps milestone keys to speak event types', () => {
    expect(mapMilestoneToSpeakEvent('start')).toBe('agent_start');
    expect(mapMilestoneToSpeakEvent('thinking:0')).toBe('thinking');
    expect(mapMilestoneToSpeakEvent('tool:1')).toBe('tool');
    expect(mapMilestoneToSpeakEvent('edit:2')).toBe('edit');
    expect(mapMilestoneToSpeakEvent('done')).toBe('done');
    expect(mapMilestoneToSpeakEvent('failed')).toBe('failed');
  });

  it('speaks live thinking as the run-start intent in minimal and conversational modes', () => {
    const spokenBlock =
      "I'll start by checking the screenshot and any recent terminal or log output.";
    expect(
      shouldSpeakLiveThinkingBlock({
        narration: 'minimal',
        spokenBlock,
      }),
    ).toBe(true);
    expect(
      shouldSpeakLiveThinkingBlock({
        narration: 'conversational',
        spokenBlock,
      }),
    ).toBe(true);
    expect(
      shouldSpeakLiveThinkingBlock({
        narration: 'off',
        spokenBlock,
      }),
    ).toBe(false);
    expect(
      shouldSpeakLiveThinkingBlock({
        narration: 'minimal',
        spokenBlock: 'They want table rendering to',
      }),
    ).toBe(false);
  });

  it('suppresses repeat wait-progress and near-duplicate thinking speech', () => {
    const waitLine =
      'The Metro cache is active and the build is still progressing.';
    expect(
      shouldSpeakLiveThinkingBlock({
        narration: 'conversational',
        spokenBlock: waitLine,
        isWaitProgress: true,
        alreadySpokeWaitProgress: false,
      }),
    ).toBe(true);
    expect(
      shouldSpeakLiveThinkingBlock({
        narration: 'conversational',
        spokenBlock: waitLine,
        isWaitProgress: true,
        alreadySpokeWaitProgress: true,
      }),
    ).toBe(false);
    expect(
      shouldSpeakLiveThinkingBlock({
        narration: 'conversational',
        spokenBlock: waitLine,
        lastSpokenBlock: waitLine,
        similarityToLast: 0.95,
      }),
    ).toBe(false);
  });

  it('gates progress milestones to avoid canned status spam', () => {
    expect(
      shouldNarrateProgressMilestone({ eventType: 'run_started', narration: 'minimal' }),
    ).toBe(false);
    expect(
      shouldNarrateProgressMilestone({ eventType: 'research_started', narration: 'minimal' }),
    ).toBe(false);
    expect(
      shouldNarrateProgressMilestone({ eventType: 'approval_required', narration: 'minimal' }),
    ).toBe(true);

    expect(
      shouldNarrateProgressMilestone({ eventType: 'run_started', narration: 'conversational' }),
    ).toBe(false);
    expect(
      shouldNarrateProgressMilestone({ eventType: 'verified_complete', narration: 'conversational' }),
    ).toBe(false);
    expect(
      shouldNarrateProgressMilestone({ eventType: 'stream_error', narration: 'conversational' }),
    ).toBe(true);
  });
});
