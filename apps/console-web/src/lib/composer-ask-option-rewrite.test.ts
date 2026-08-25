import { beforeEach, describe, expect, it } from 'vitest';

import { markQuestionAnswered, questionAnswerKey } from './answered-agent-questions';
import { rewriteComposerAskOptionAnswer } from './composer-ask-option-rewrite';

describe('rewriteComposerAskOptionAnswer', () => {
  beforeEach(() => {
    // markQuestionAnswered is session-global; use unique prompts per case.
  });

  it('rewrites a bare option digit to the Continue payload', () => {
    const askContent = [
      ':::ask How should I clear the canary gate?',
      '- 1 | Fix the tree and retry',
      '- 2 | Skip canary for now',
      '- 3 | Force publish anyway',
      ':::',
    ].join('\n');
    const rewritten = rewriteComposerAskOptionAnswer('3', [
      {
        message_id: 'msg_ask_rewrite',
        role: 'agent',
        content: askContent,
      },
    ]);
    expect(rewritten?.option.id).toBe('3');
    expect(rewritten?.content).toContain('Selected option 3: Force publish anyway');
    expect(rewritten?.content).toContain('(answer to: How should I clear the canary gate?)');
  });

  it('rewrites a bare digit for a plain cross-platform numbered question', () => {
    const content = [
      'What should the workspace validation cover?',
      '',
      '1. Graduation groups',
      '2. Confirmed but unallocated children',
      '3. Cross-system sync',
      '4. All of the above',
    ].join('\n');

    const rewritten = rewriteComposerAskOptionAnswer('4', [
      {
        message_id: 'msg_plain_cross_platform_ask',
        role: 'agent',
        content,
      },
    ]);

    expect(rewritten?.content).toContain('Selected option 4: All of the above');
    expect(rewritten?.content).toContain('(answer to: What should the workspace validation cover?)');
  });

  it('ignores bare digits when there is no open ask', () => {
    expect(
      rewriteComposerAskOptionAnswer('3', [
        { message_id: 'msg_plain', role: 'agent', content: 'All clear.' },
      ]),
    ).toBeNull();
  });

  it('ignores bare digits for already-marked asks', () => {
    const prompt = 'How should I clear the canary gate?';
    markQuestionAnswered('msg_marked_ask', prompt);
    expect(questionAnswerKey('msg_marked_ask', prompt)).toContain('msg_marked_ask');
    const askContent = [
      `:::ask ${prompt}`,
      '- 1 | Fix the tree and retry',
      '- 2 | Skip canary for now',
      '- 3 | Force publish anyway',
      ':::',
    ].join('\n');
    expect(
      rewriteComposerAskOptionAnswer('3', [
        {
          message_id: 'msg_marked_ask',
          role: 'agent',
          content: askContent,
        },
      ]),
    ).toBeNull();
  });
});
