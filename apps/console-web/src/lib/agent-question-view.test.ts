import { describe, expect, it } from 'vitest';

import {
  formatQuestionAnswer,
  parseAskOptions,
  tryParseClarifyingMarkdown,
} from './agent-question-view';
import { parseAgentTranscriptBlocks } from './agent-transcript-blocks';

describe('agent question view', () => {
  it('parses :::ask fences into question segments', () => {
    const segments = parseAgentTranscriptBlocks(
      [
        ':::ask What should this plan focus on?',
        '- 1 | Employee / coordination gaps',
        '- 2 | Mobile remote control',
        '- 3 | Both, phased',
        ':::',
      ].join('\n'),
    );
    expect(segments).toHaveLength(1);
    expect(segments[0]).toMatchObject({
      kind: 'question',
      prompt: 'What should this plan focus on?',
    });
    if (segments[0]?.kind === 'question') {
      expect(segments[0].options).toEqual([
        { id: '1', label: 'Employee / coordination gaps' },
        { id: '2', label: 'Mobile remote control' },
        { id: '3', label: 'Both, phased' },
      ]);
    }
  });

  it('upgrades plain clarifying markdown into a question card', () => {
    const text = [
      'What should this plan focus on?',
      '',
      '1. Employee / coordination gaps',
      '2. Mobile remote control',
      '3. Both, phased',
      '',
      'Reply with `1`, `2`, or `3`.',
    ].join('\n');
    const parsed = tryParseClarifyingMarkdown(text);
    expect(parsed?.options).toHaveLength(3);
    expect(parsed?.prompt.toLowerCase()).toContain('what should this plan focus');

    const segments = parseAgentTranscriptBlocks(text);
    expect(segments.some((segment) => segment.kind === 'question')).toBe(true);
  });

  it('parses pipe options and formats answers with id and label', () => {
    expect(
      parseAskOptions(['- 1 | Alpha', '- 2 | Beta']),
    ).toEqual([
      { id: '1', label: 'Alpha' },
      { id: '2', label: 'Beta' },
    ]);
    expect(formatQuestionAnswer({ id: '3', label: 'Both, phased' })).toBe(
      'Selected option 3: Both, phased',
    );
    expect(
      formatQuestionAnswer({ id: '3', label: 'Both, phased' }, 'What should this plan focus on?'),
    ).toBe(
      ['Selected option 3: Both, phased', '(answer to: What should this plan focus on?)'].join(
        '\n',
      ),
    );
  });
});
