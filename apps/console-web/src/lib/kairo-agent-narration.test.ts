import { describe, expect, it } from 'vitest';

import {
  liveThinkingText,
  narrationForCompletion,
  narrationMilestonesForDelta,
  streamingActivityLabel,
} from './kairo-agent-narration';

const STAGE_1 = ':::thinking\nChecking the file';
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
});
