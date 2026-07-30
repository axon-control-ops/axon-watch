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

  it('collapses the latest ask when the operator types a bare option digit', () => {
    const askContent = [
      ':::ask How should I clear the canary gate?',
      '- 1 | Fix the tree and retry',
      '- 2 | Skip canary for now',
      '- 3 | Force publish anyway',
      ':::',
    ].join('\n');
    const items = [
      { kind: 'message', message: { role: 'agent', content: askContent, message_id: 'msg_ask' } },
      { kind: 'message', message: { role: 'operator', content: '3' } },
    ];

    expect(
      answeredOptionForQuestion(
        items,
        'msg_ask',
        'How should I clear the canary gate?',
        [
          { id: '1', label: 'Fix the tree and retry' },
          { id: '2', label: 'Skip canary for now' },
          { id: '3', label: 'Force publish anyway' },
        ],
        0,
      )?.id,
    ).toBe('3');
  });

  it('does not collapse an older ask from a bare digit on a newer agent turn', () => {
    const olderAsk = [
      ':::ask How should I gather online vendor facts?',
      '- 1 | Create a new restricted API key',
      '- 2 | You will provide keys',
      '- 3 | Skip Google Custom Search',
      ':::',
    ].join('\n');
    const newerAsk = [
      ':::ask How should I clear the canary gate?',
      '- 1 | Fix the tree and retry',
      '- 2 | Skip canary for now',
      '- 3 | Force publish anyway',
      ':::',
    ].join('\n');
    const items = [
      { kind: 'message', message: { role: 'agent', content: olderAsk, message_id: 'msg_old' } },
      { kind: 'message', message: { role: 'agent', content: newerAsk, message_id: 'msg_new' } },
      { kind: 'message', message: { role: 'operator', content: '3' } },
    ];

    expect(
      answeredOptionForQuestion(
        items,
        'msg_old',
        'How should I gather online vendor facts?',
        OPTIONS,
        0,
      ),
    ).toBeNull();

    expect(
      answeredOptionForQuestion(
        items,
        'msg_new',
        'How should I clear the canary gate?',
        [
          { id: '1', label: 'Fix the tree and retry' },
          { id: '2', label: 'Skip canary for now' },
          { id: '3', label: 'Force publish anyway' },
        ],
        1,
      )?.id,
    ).toBe('3');
  });
});
