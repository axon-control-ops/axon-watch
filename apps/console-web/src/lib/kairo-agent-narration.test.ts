import { describe, expect, it } from 'vitest';

import {
  liveThinkingText,
  narrationForCompletion,
  narrationMilestonesForDelta,
  resolveStreamingActivity,
  spokenCompletionSummary,
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
      "I'm starting to analyze the rendering issues the user wants fixed. They want table rendering to work in markdown previews.",
    );
    expect(view.liveBodyTruncated).toBe(true);
  });

  it('hides pure user-meta thinking from the VAXON live line', () => {
    const view = resolveStreamingActivity(':::thinking\nThe user is asking whether\n');
    expect(view.label).toBe('VAXON — Agent running…');
    expect(view.liveBodyFull).toBeNull();
    expect(view.liveBodySpoken).toBeNull();
  });
});

describe('narrationMilestonesForDelta', () => {
  it('emits structured milestones without speakable copy', () => {
    const first = narrationMilestonesForDelta('', STAGE_1);
    expect(first).toEqual([{ key: 'thinking:0', message: 'On it…' }]);

    const second = narrationMilestonesForDelta(STAGE_1, STAGE_2);
    expect(second[0]).toMatchObject({ key: 'tool:0', toolLabel: 'Read README.md' });

    const third = narrationMilestonesForDelta(STAGE_2, STAGE_3);
    expect(third[0]).toMatchObject({ key: 'edit:0', editPath: 'README.md' });
  });
});

describe('narrationForCompletion', () => {
  it('captures edit metadata and spoken summary for voice script', () => {
    expect(narrationForCompletion(STAGE_3)).toMatchObject({
      key: 'done',
      editPath: 'README.md',
      editCount: 1,
      message: 'DONE',
    });
    expect(narrationForCompletion('plain reply')).toEqual({ key: 'done', message: 'plain reply' });
  });

  it('extracts a spoken completion summary from the final reply', () => {
    const content = `${STAGE_2}\n\nI updated the scrollback limit and added a test. The terminal should stop clipping now.`;
    expect(spokenCompletionSummary(content)).toBe(
      'I updated the scrollback limit and added a test. The terminal should stop clipping now.',
    );
  });

  it('marks Lane B runtime failures instead of done', () => {
    const failure =
      "Lane B (agent) cannot start because no CLI runtime is ready: ActionRequiredError: You're out of usage.";
    expect(narrationForCompletion(failure)).toEqual({ key: 'failed', message: 'Failed' });
  });

  it('uses a short waiting line when the reply ends with a reproduce pause', () => {
    const content = [
      'Root cause looks like speech cleanup.',
      '',
      ':::debug-reproduce',
      '1. Keep Debug mode on.',
      '2. Note what voice says.',
      ':::',
    ].join('\n');
    expect(narrationForCompletion(content)).toEqual({
      key: 'done',
      message: 'Waiting for you to reproduce the bug.',
      verbatim: true,
    });
    expect(spokenCompletionSummary(content)).not.toContain('Keep Debug mode on');
  });
});
