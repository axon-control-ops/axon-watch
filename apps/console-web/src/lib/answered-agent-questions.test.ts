import { describe, expect, it } from 'vitest';

import {
  isQuestionMarkedAnswered,
  markQuestionAnswered,
  matchQuestionAnswerFromUserText,
} from './answered-agent-questions';

const OPTIONS = [
  { id: '1', label: 'Walk me through enabling it' },
  { id: '2', label: 'Run the sandbox safety checks' },
  { id: '3', label: 'Leave it as-is' },
];

describe('answered-agent-questions', () => {
  it('marks and recalls answered ask cards', () => {
    markQuestionAnswered('msg_1', 'What should we do next with the sandbox?');
    expect(
      isQuestionMarkedAnswered('msg_1', 'What should we do next with the sandbox?'),
    ).toBe(true);
  });

  it('matches bare option ids and Selected option payloads', () => {
    expect(matchQuestionAnswerFromUserText(OPTIONS, '1')?.label).toBe(
      'Walk me through enabling it',
    );
    expect(
      matchQuestionAnswerFromUserText(
        OPTIONS,
        'Selected option 2: Run the sandbox safety checks\n(answer to: Ready?)',
      )?.id,
    ).toBe('2');
  });
});
