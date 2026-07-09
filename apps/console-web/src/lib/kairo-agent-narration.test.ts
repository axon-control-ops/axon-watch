import { describe, expect, it } from 'vitest';

import {
  liveThinkingText,
  narrationForCompletion,
  narrationMilestonesForDelta,
  resolveStreamingActivity,
  streamingActivityLabel,
} from './kairo-agent-narration';

const LONG_THINKING_BODY =
  "I'm starting to analyze the rendering issues the user wants fixed. They want table rendering to work in markdown previews.";
const STAGE_1 = ':::thinking\nChecking the file';
const STAGE_1_LONG = `:::thinking\n${LONG_THINKING_BODY}`;
const STAGE_2 = ':::thinking\nChecking the file.\n:::\n\n:::tool Read README.md\n';
const STAGE_3 = `${STAGE_2}\n:::edit README.md +1 -0\n--- a\n+++ b\n+<!-- hi -->\n:::\nDONE`;

describe('liveThinkingText', () => {
  it('returns the open thinking body while streaming', () => {
    expect(liveThinkingText(STAGE_1)).toBe('Checking the file');
    expect(liveThinkingText(STAGE_2)).toBe('Checking the file.');
  });
});

describe('streamingActivityLabel', () => {
  it('prefers live thinking text for KAIRO status', () => {
    expect(streamingActivityLabel(STAGE_1)).toBe('VAXON — Checking the file');
  });
});

describe('resolveStreamingActivity', () => {
  it('exposes full and spoken thinking bodies separately from display label', () => {
    const view = resolveStreamingActivity(STAGE_1_LONG);
    expect(view.label.startsWith('VAXON —')).toBe(true);
    expect(view.label.endsWith('…')).toBe(true);
    expect(view.liveBodyFull).toBe(LONG_THINKING_BODY);
    expect(view.liveBodySpoken).toBe(
      "I'm starting to analyze the rendering issues the user wants fixed.",
    );
    expect(view.liveBodyTruncated).toBe(true);
  });
});

describe('narrationMilestonesForDelta', () => {
  it('emits structured milestones without speakable copy', () => {
    const first = narrationMilestonesForDelta('', STAGE_1);
    expect(first).toEqual([{ key: 'thinking:0', message: 'Thinking…' }]);

    const second = narrationMilestonesForDelta(STAGE_1, STAGE_2);
    expect(second[0]).toMatchObject({ key: 'tool:0', toolLabel: 'Read README.md' });

    const third = narrationMilestonesForDelta(STAGE_2, STAGE_3);
    expect(third[0]).toMatchObject({ key: 'edit:0', editPath: 'README.md' });
  });
});

describe('narrationForCompletion', () => {
  it('captures edit metadata for voice script', () => {
    expect(narrationForCompletion(STAGE_3)).toMatchObject({
      key: 'done',
      editPath: 'README.md',
      editCount: 1,
    });
    expect(narrationForCompletion('plain reply')).toEqual({ key: 'done', message: 'Done' });
  });

  it('marks Lane B runtime failures instead of done', () => {
    const failure =
      "Lane B (agent) cannot start because no CLI runtime is ready: ActionRequiredError: You're out of usage.";
    expect(narrationForCompletion(failure)).toEqual({ key: 'failed', message: 'Failed' });
  });
});
