import { describe, expect, it } from 'vitest';

import { markQuestionAnswered } from './answered-agent-questions';
import {
  answeredOptionForQuestion,
  followupCitesQuestionPrompt,
} from './conversation-seam-question-answers';

const OPTIONS = [
  { id: '1', label: 'Create a new restricted API key' },
  { id: '2', label: 'You will provide keys' },
  { id: '3', label: 'Skip Google Custom Search' },
];

describe('conversation seam question answers', () => {
  it('does not collapse older ask cards from a later unrelated answer', () => {
    const items = [
      { kind: 'message', message: { role: 'agent', content: 'older ask' } },
      { kind: 'message', message: { role: 'agent', content: 'newer ask' } },
      {
        kind: 'message',
        message: {
          role: 'operator',
          content: [
            'Selected option 1: Create a new restricted API key',
            '(answer to: How should we set up a VAXON-dedicated Google search key?)',
          ].join('\n'),
        },
      },
    ];

    expect(
      answeredOptionForQuestion(
        items,
        'msg_older',
        'How should I gather online vendor facts?',
        OPTIONS,
        0,
      ),
    ).toBeNull();

    expect(
      answeredOptionForQuestion(
        items,
        'msg_newer',
        'How should we set up a VAXON-dedicated Google search key?',
        OPTIONS,
        1,
      )?.id,
    ).toBe('1');
  });

  it('collapses only the marked card when Continue was pressed', () => {
    markQuestionAnswered('msg_marked', 'How should we set up a VAXON-dedicated Google search key?');
    const items = [
      { kind: 'message', message: { role: 'agent', content: 'ask' } },
      {
        kind: 'message',
        message: {
          role: 'operator',
          content: [
            'Selected option 2: You will provide keys',
            '(answer to: How should we set up a VAXON-dedicated Google search key?)',
          ].join('\n'),
        },
      },
    ];

    expect(
      answeredOptionForQuestion(
        items,
        'msg_marked',
        'How should we set up a VAXON-dedicated Google search key?',
        OPTIONS,
        0,
      )?.id,
    ).toBe('2');
  });

  it('detects answer-to trailers for the exact prompt', () => {
    expect(
      followupCitesQuestionPrompt(
        'Selected option 1: A\n(answer to: Exact prompt here)',
        'Exact prompt here',
      ),
    ).toBe(true);
    expect(
      followupCitesQuestionPrompt(
        'Selected option 1: A\n(answer to: Exact prompt here)',
        'A different prompt',
      ),
    ).toBe(false);
  });
});
